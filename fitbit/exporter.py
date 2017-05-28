import argparse
import httplib2
import json
import os
import pickle
import socket
import struct

from base64 import urlsafe_b64encode
from datetime import datetime
from functools import partial
from graphitesend import GraphiteClient
from oauth2client import tools
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.file import Storage

API_HOST = 'https://api.fitbit.com'
API_URL = "%s/1/user/-" % API_HOST

EXPORTER_HOME = "%s/.fitbit-exporter" % os.environ['HOME']
CREDENDIAL_STORE = "%s/client_secrets.json" % EXPORTER_HOME

CLIENT_ID = os.environ['CLIENT_ID']
CLIENT_SECRET = os.environ['CLIENT_SECRET']
AUTHORIZATION = urlsafe_b64encode(bytes("%s:%s" % (CLIENT_ID, CLIENT_SECRET), 'utf-8')).decode('utf-8')

UTF_8 = 'utf-8'

ACTIVITIES = ['heart', 'steps', 'floors', 'calories', 'elevation', 'distance']

class FitBitError(Exception):
    def __init__(self, msg):
        super().__init__(msg)


class FitBit:
    def __init__(self, args):
        self.http = httplib2.Http()
        self.__setup(args)
        self.__authenticate(args).authorize(self.http)
        self.date = args.date
        self.end = args.period
        self.period = args.period

    def __setup(self, args):
        if not os.path.exists(EXPORTER_HOME):
            os.mkdir(EXPORTER_HOME)
        if not os.path.exists(CREDENDIAL_STORE):
            open(CREDENDIAL_STORE, 'w+').close()
        return EXPORTER_HOME, CREDENDIAL_STORE

    def __authenticate(self, args):
        flow = OAuth2WebServerFlow(
                auth_uri='https://www.fitbit.com/oauth2/authorize',
                token_uri='%s/oauth2/token' % API_HOST,
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                scope='activity sleep weight heartrate',
                user_agent='fitbit-exporter/1.1',
                authorization_header="Basic %s" % AUTHORIZATION)
        storage = Storage(CREDENDIAL_STORE)
        credz = storage.get()
        if credz is None or credz.invalid:
            credz = tools.run_flow(flow, storage, args)
        return credz

    def _body(self, resource):
        resp, content = self.http.request(
                "%s/body/%s/date/%s/%s.json" %
                (API_URL, resource, self.date, self.end))
        if resp.status == 200:
            return json.loads(content.decode(UTF_8))
        else:
            raise FitBitError("Unable to get %s: %s\n%s" %
                    (resource, resp, content))

    def _activities(self, activity, granularity):
        resp, content = self.http.request(
                "%s/activities/%s/date/%s/1d/%s.json" %
                (API_URL, activity, self.date, granularity))
        if resp.status == 200:
            return json.loads(content.decode(UTF_8))
        else:
            raise FitBitError("Unable to get %s activity: %s\n%s" %
                    (activity, resp, content))

    def steps(self):
        return self._activities('steps', '1min')

    def heart(self):
        return self._activities('heart', '1sec')

    def floors(self):
        return self._activities('floors', '1min')

    def elevation(self):
        return self._activities('elevation', '1min')

    def calories(self):
        return self._activities('calories', '1min')

    def distance(self):
        return self._activities('distance', '1min')

    def body(self, resource):
        return self._body(resource)


class Graphite:
    def __init__(self, connect, prefix, tags):
        self.prefix = prefix
        self.connection = connect

    def __prefix(self, metric):
        return "%s.%s" % (self.prefix, metric[0])

    def send(self, metrics):
        prefixed = [(self.__prefix(t), (t[1][0], t[1][1])) for t in metrics]
        payload = pickle.dumps(prefixed, protocol=2)

        s = socket.socket()
        s.connect(self.connection)
        s.sendall(struct.pack('!L', len(payload)))
        s.sendall(payload)
        s.close()

class Influx:
    def __init__(self, connect, prefix, tags):
        self.prefix = prefix
        self.connection = connect
        self.tags = tags
        self.http = httplib2.Http()

    def __prefix(self, metric):
        return "%s.%s" % (self.prefix, metric[0])

    def send(self, metrics):
        tags = ",".join(self.tags)
        lines = [
            "%s,%s value=%s %d" % (self.__prefix(t), tags, t[1][1], t[1][0] * 1000 * 1000000)
            for t in metrics ]
        payload = "\n".join(lines)

        host = "%s:%s" % (self.connection[0], self.connection[1])
        uri = "http://%s/write?db=graphite" % host
        resp, content = self.http.request(uri, method="POST", body=payload)

        if resp.status != 204:
            raise FitBitError(
                "Unable to send InfluxDB data: %s\n%s" % (resp, content)
            )



def _parse_body(resource, raw_data):
    data = []
    for d in raw_data["body-%s" % resource]:
        instant = datetime.strptime(d['dateTime'], '%Y-%m-%d')
        epoch = instant.strftime('%s')
        data.append((resource, (int(epoch), float(d['value']))))
    return data

def _parse_activities(activity, raw_data):
    data = []
    date = raw_data["activities-%s" % activity][0]['dateTime']
    for m in raw_data["activities-%s-intraday" % activity]['dataset']:
        instant = "%s %s" % (date, m['time'])
        instant = datetime.strptime(instant, '%Y-%m-%d %H:%M:%S')
        epoch = instant.strftime('%s')
        data.append((activity, (int(epoch), int(m['value']))))
    return data

def _try_query(name, query, parser, reporter):
    try:
        reporter(parser(name, query()))
    except Error as e:
        print(str(e))
        return None


def main(argv=None):
    parser = argparse.ArgumentParser(parents=[tools.argparser])

    ingester_group = parser.add_mutually_exclusive_group(required=True)
    ingester_group.add_argument('--graphite', metavar='url',
            help='Use a graphite host, for example, localhost:2004.')
    ingester_group.add_argument('--influx', metavar='url',
            help='Use an influx host, for example, localhost:8086.')

    parser.add_argument('-t', '--tag', required=False, default=[],
            metavar='key=value', action='append',
            help='A tag for the storage system, if supported.')

    parser.add_argument('--debug', action='store_true', default=False)
    parser.add_argument('--period', default='1d', required=False, help='The end period. Default of 1 day.')

    parser.add_argument('--all', action='store_true', default=False, help='Export all known types.')
    parser.add_argument('--body', action='store_true', default=False, help='Export body data.')
    for a in ACTIVITIES:
        parser.add_argument("--%s" % a, action='store_true', default=False, help="Export %s data." % a)

    parser.add_argument('date', help='The start date to export in the format of YYYY-mm-dd, or \'today\'.')
    args = parser.parse_args()
    if args.debug:
        httplib2.debuglevel=4

    ingester_clazz = Graphite if args.graphite else Influx
    connection = (args.graphite or args.influx).split(':')
    ingester = ingester_clazz((connection[0], int(connection[1])), 'fitness', args.tag).send
    client = FitBit(args)

    for activity in ACTIVITIES:
        if args.__getattribute__(activity) or args.all:
            _try_query(activity, client.__getattribute__(activity), _parse_activities, ingester)

    if args.body or args.all:
        _try_query('weight', partial(client.body, 'weight'), _parse_body, ingester)
        _try_query('fat', partial(client.body, 'fat'), _parse_body, ingester)
        _try_query('bmi', partial(client.body, 'bmi'), _parse_body, ingester)


if __name__ == "__main__":
    main()
