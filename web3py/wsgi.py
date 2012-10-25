import os
import sys
import re
import traceback
import logging
import time
import datetime
import optparse

from .rocket import Rocket
from .http import HTTP
from .expose import expose
from .dal import DAL, Field
from .current import Current
from .stream import stream_file_handler

logging.basicConfig(level=logging.INFO)

GLOBAL = dict()
REGEX_STATIC = re.compile('^/(?P<a>.*?)/static/(?P<v>_\d+\.\d+\.\d+/)?(?P<f>.*?)$')
REGEX_RANGE = re.compile('^\s*(?P<start>\d*).*(?P<stop>\d*)\s*$')


def dynamic_handler(environ, start_response):
    try:
        current = expose.run(Current(environ))
        http = HTTP(current.status_code,current.output,
                    headers=current.response_headers,
                    cookies=current.response_cookies)
    except HTTP:
        http = sys.exc_info()[1]
    return http.to(environ, start_response)


def static_handler(environ, start_response):
    static_file = None
    path_info = environ['PATH_INFO']
    static_match = REGEX_STATIC.match(path_info) 
    if static_match: # check if visitor has requested a static file        
        app, version, filename = static_match.group('a', 'v','f')        
        static_file = os.path.abspath(
            os.path.join(GLOBAL['apps_folder'], app, 'static', filename))
        # prevent directory traversal attacks
        if static_file.startswith(GLOBAL['apps_folder']):            
            return stream_file_handler(
                environ, start_response, static_file, version,
                GLOBAL['stream_block_size'])
        else:
            return HTTP(404).to(environ, start_response)
    else: # else call the dynamic handler
        data = dynamic_handler(environ, start_response)
        if isinstance(data, HTTP.stream): 
            return stream_file_handler(
                environ, start_response, data.static_file, 
                data.version, data.headers,
                GLOBAL['stream_block_size'])
        else:
            return data

def error_handler(environ, start_response):
    t0 = time.time()
    app = environ['w3p.application'] = (environ.get('PATH_INFO', None) or '/unknown').split('/')[1]
    now = environ['w3p.now'] = datetime.datetime.now()
    try:
        return static_handler(environ, start_response)
    except Exception:
        error = str(sys.exc_info()[1])
        tb = traceback.format_exc()
        logging.error(tb)
        db = GLOBAL['db']
        try:
            ticket = db.error.insert(
                app=app,error_timestamp=now,
                remote_addr=environ['REMOTE_ADDR'],
                error=error,traceback=tb)
            db.commit()
            body = '<html><body>ticket-%s</body></html>' % ticket 
        except Exception:
            error = sys.exc_info()[1]
            db.rollback()            
            body = '<html><body>Internal error: %s</body></html>'
        return HTTP(500,body).to(environ, start_response)
    finally:
        dt = time.time() - t0
        logging.info('%s %s %s' % (environ['REMOTE_ADDR'], environ['PATH_INFO'], dt))

    
class FileSubset(object):
    """ class needed to handle RANGE currents """
    def __init__(self, stream, start, stop):
        self.stream = stream
        self.stream.seek(start)
        self.size = stop - start

    def read(self, bytes=None):
        bytes = self.size if bytes is None else max(bytes, self.size)
        if bytes:
            data = self.stream.read(bytes)
            self.size -= bytes
            return data
        else:
            return ''

    def close(self):
        self.stream.close()
            

def define_error_table(db):
    db.define_table(
        'error',
        Field('app'),
        Field('error_timestamp'),
        Field('remote_addr'),
        Field('error'),
        Field('traceback'),
        Field('status','text'),
        Field('file_content','text')) 


def run():
    parser = optparse.OptionParser()
    parser.add_option("-i", "--ip", dest="ip", default="127.0.0.1",
                      help="ip address of the network interface")
    parser.add_option("-p", "--port", dest="port", default="8000",
                      help="post where to run web server")
    parser.add_option(
        "-a", "--apps_folder", dest="apps_folder", default=None,
        help="folder containing apps_folder")
    (options, args) = parser.parse_args()
    GLOBAL['command_line_options'] = options
    GLOBAL['stream_block_size'] = 10 ** 5
    GLOBAL['apps_folder'] = options.apps_folder or os.path.join(
        os.getcwd(), 'apps')
    GLOBAL['vars_folder'] = os.path.join(os.getcwd(),'vars')
    if not os.path.exists(GLOBAL['apps_folder']):
        os.mkdir(GLOBAL['apps_folder'])
    if not os.path.exists(GLOBAL['vars_folder']):
        os.mkdir(GLOBAL['vars_folder'])
    GLOBAL['routes_in'] = []
    GLOBAL['routes_out'] = []
    GLOBAL['db_uri'] = 'sqlite://errors.db'
    GLOBAL['db'] = DAL(GLOBAL['db_uri'],folder=GLOBAL['vars_folder'])
    define_error_table(GLOBAL['db'])
    expose.scan_apps(GLOBAL['apps_folder'])
    r = Rocket((options.ip, int(options.port)), 'wsgi', {'wsgi_app': error_handler})
    r.start()
