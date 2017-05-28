fitbit-exporter
===============

A quick and dirty, as-is tool that can export intra-day Fitbit data to Graphite
or InfluxDB. To use this application, you will have to create a new Fitbit
application under your account.

Usage
=====

`fitbit-exporter` assumes you have a `client_id` and `client_secret`
for your application and expects them to be set into environmental
variables. Upon first run, `fitbit-exporter` will go through the OAuth
flow and allow this application access to your account.

```
export CLIENT_ID=1
export CLIENT_SECRET=2

./fitbit-exporter
usage: fitbit-exporter [-h] [--auth_host_name AUTH_HOST_NAME]
                       [--noauth_local_webserver]
                       [--auth_host_port [AUTH_HOST_PORT [AUTH_HOST_PORT ...]]]
                       [--logging_level {DEBUG,INFO,WARNING,ERROR,CRITICAL}]
                       (--graphite url | --influx url) [-t key=value]
                       [--debug] [--period PERIOD] [--all] [--body] [--heart]
                       [--steps] [--floors] [--calories] [--elevation]
                       [--distance]
                       date

positional arguments:
  date                  The start date to export in the format of YYYY-mm-dd,
                        or 'today'.

optional arguments:
  -h, --help            show this help message and exit
  --auth_host_name AUTH_HOST_NAME
                        Hostname when running a local web server.
  --noauth_local_webserver
                        Do not run a local web server.
  --auth_host_port [AUTH_HOST_PORT [AUTH_HOST_PORT ...]]
                        Port web server should listen on.
  --logging_level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set the logging level of detail.
  --graphite url        Use a graphite host, for example, localhost:2004.
  --influx url          Use an influx host, for example, localhost:8086.
  -t key=value, --tag key=value
                        A set of tags for the storage system, if supported. This argument may be repeated.
  --debug
  --period PERIOD       May be end date or period. Default of 1d.
  --all                 Export all known types.
  --body                Export body data.
  --heart               Export heart data.
  --steps               Export steps data.
  --floors              Export floors data.
  --calories            Export calories data.
  --elevation           Export elevation data.
  --distance            Export distance data.
```
