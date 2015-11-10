import argparse
import httplib2
import json
import os
import socket
import pickle
import struct

from datetime import datetime
from graphitesend import GraphiteClient
from base64 import urlsafe_b64encode
from oauth2client.file import Storage
from oauth2client.client import OAuth2WebServerFlow
from oauth2client import tools

API_HOST = 'https://api.fitbit.com'
API_URL = "%s/1/user/-" % API_HOST

EXPORTER_HOME = "%s/.fitbit-exporter" % os.environ['HOME']
CREDENDIAL_STORE = "%s/client_secrets.json" % EXPORTER_HOME

CLIENT_ID = os.environ['CLIENT_ID']
CLIENT_SECRET = os.environ['CLIENT_SECRET']
AUTHORIZATION = urlsafe_b64encode(bytes("%s:%s" % (CLIENT_ID, CLIENT_SECRET), 'utf-8')).decode('utf-8')

UTF_8 = 'utf-8'

class FitBitError(Exception):
    def __init__(self, msg):
        super().__init__(msg)

class FitBitConnection(httplib2.Http):
    """
    FitBit requires an Authorization header to be present on every request.
    Out of the box, Google's oauth2 client does not do this. As such, this
    is a basic override to inject missing headers.
    """

    def __init__(self, cache=None, timeout=None,
                 proxy_info=httplib2.proxy_info_from_environment,
                 ca_certs=None, disable_ssl_certificate_validation=False):
        super().__init__(cache, timeout, proxy_info, ca_certs,
                         disable_ssl_certificate_validation)

    def request(self, uri, method="GET", body=None, headers=None,
                redirections=httplib2.DEFAULT_MAX_REDIRECTS,
                connection_type=None):
        if headers is None:
            headers = {}
        if 'Authorization' not in headers:
            headers.update({'Authorization': 'Basic ' + AUTHORIZATION})
        return super().request(uri, method=method, body=body, headers=headers,
                               redirections=redirections,
                               connection_type=connection_type)

class FitBit:
    def __init__(self, args):
        self.http = httplib2.Http()
        #self.http = FitBitConnection()
        self.__setup(args)
        self.__authenticate(args).authorize(self.http)
        self.date = args.date

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
                user_agent='fitbit-exporter/1.0',
                authorization_header="Basic " + AUTHORIZATION)
        storage = Storage(CREDENDIAL_STORE)
        credz = storage.get()
        if credz is None or credz.invalid:
            credz = tools.run_flow(flow, storage, args)
        return credz

    def _activities(self, activity, granularity):
        resp, content = self.http.request(
                "%s/activities/%s/date/%s/1d/%s.json" %
                (API_URL, activity, self.date, granularity))
        if resp.status == 200:
            return json.loads(content.decode(UTF_8))
        else:
            raise FitBitError("Unable to get %s activity: %s" % 
                    (activity, resp))

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


class Graphite:

    def __init__(self, prefix, host='localhost', port=2004):
        self.prefix = prefix
        self.connection = (host, port)

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


def _parse_activities(activity, raw_data):
    data = []
    date = raw_data["activities-%s" % activity][0]['dateTime']
    for m in raw_data["activities-%s-intraday" % activity]['dataset']:
        instant = "%s %s" % (date, m['time'])
        instant = datetime.strptime(instant, '%Y-%m-%d %H:%M:%S')
        epoch = instant.strftime('%s')
        data.append((activity, (int(epoch), int(m['value']))))
    return data

def _try_query(activity, graphite, fn):
    try:
        graphite.send(_parse_activities(activity, fn()))
    except FitBitError as e:
        print(str(e))

def main(argv=None):
    parser = argparse.ArgumentParser(parents=[tools.argparser])
    parser.add_argument('--debug', action='store_true', default=False)
    parser.add_argument('--all', action='store_true', default=False, help='Export all known types.')
    parser.add_argument('--heart', action='store_true', default=False, help='Export heart data.')
    parser.add_argument('--steps', action='store_true', default=False, help='Export steps data.')
    parser.add_argument('--floors', action='store_true', default=False, help='Export floors data.')
    parser.add_argument('--calories', action='store_true', default=False, help='Export calories data.')
    parser.add_argument('--elevation', action='store_true', default=False, help='Export elevation data.')
    parser.add_argument('--distance', action='store_true', default=False, help='Export distance data.')
    parser.add_argument('date', help='The date to export in the format of YYYY-mm-dd, or \'today\'.')
    args = parser.parse_args()
    if args.debug:
        httplib2.debuglevel=4

    graphite = Graphite('fitness')
    client = FitBit(args)

    if args.heart or args.all:
        _try_query('heart', graphite, client.heart)

    if args.steps or args.all:
        _try_query('steps', graphite, client.steps)

    if args.floors or args.all:
        _try_query('floors', graphite, client.floors)

    if args.calories or args.all:
        _try_query('calories', graphite, client.calories)

    if args.elevation or args.all:
        _try_query('elevation', graphite, client.elevation)

    if args.distance or args.all:
        _try_query('distance', graphite, client.distance)


if __name__ == "__main__":
    main()
