fitbit-exporter
===============

A quick and dirty, as-is tool that can export intra-day Fitbit data
to Graphite. To use this application, you will have to create a new
Fitbit application under your account.

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
                       [--debug] [--all] [--heart] [--steps] [--floors]
                       [--calories] [--elevation] [--distance]
                       date

positional arguments:
  date                  The date to export in the format of YYYY-mm-dd, or
                        'today'.

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
  --debug
  --all                 Export all known types.
  --heart               Export heart data.
  --steps               Export steps data.
  --floors              Export floors data.
  --calories            Export calories data.
  --elevation           Export elevation data.
  --distance            Export distance data.
```
