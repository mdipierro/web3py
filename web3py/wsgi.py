import os
import sys
import re
import traceback
import logging
import time
import datetime
import optparse

from .rocket import Rocket
from .contenttype import contenttype
from .http import HTTP
from .current import Current
from .routing import expose
from .dal import DAL, Field

logging.basicConfig(level=logging.INFO)

GLOBAL = dict()
REGEX_STATIC = re.compile('^/(.*?)/static/(.*?)$')
REGEX_RANGE = re.compile('^\s*(?P<start>\d*).*(?P<stop>\d*)\s*$')


def dynamic_handler(environ, start_response):
    try:
        current = Current(environ)
        data = expose.run(current)
        http = HTTP(current.status_code,data,
                    headers=current.response_headers,
                    cookies=current.response_cookies)
    except HTTP:
        http = sys.exc_info()[1]
    return http.to(environ, start_response)


def static_handler(environ, start_response):
    static_file = None
    path_info = environ['PATH_INFO']
    if REGEX_STATIC.match(path_info):
        path = os.path.abspath(
            os.path.join(GLOBAL['apps_folder'], path_info[1:]))
        if os.path.exists(path) and os.path.isfile(path) and path.startswith(GLOBAL['apps_folder']):
            static_file = path
        else:
            return HTTP(404).to(environ, start_response)
    else:
        data = dynamic_handler(environ, start_response)
        if isinstance(data, HTTP.stream):
            static_file = data.filename
    if static_file:
        # if user requested a static file or action returned a HTTP.stream(filename)
        # check if file can be accessed
        try:
            stream = open(static_file, 'rb')
        except IOError:
            if sys.exc_info()[1][0] in (errno.EISDIR, errno.EACCES):
                HTTP(403).to(environ, start_response)
            else:
                HTTP(404).to(environ, start_response)
        else:
            fsize = os.path.getsize(static_file)
            modified = os.path.getmtime(static_file)
            mtime = time.strftime(
                '%a, %d %b %Y %H:%M:%S GMT', time.gmtime(modified))
            headers = {}
            headers['Content-Type'] = contenttype(static_file)
            # check if file to be served as an attachment
            if environ.get('QUERY_STRING').startswith('attachment_filename='):
                headers['Content-Disposition'] = 'attachment; filanme="%s"' % \
                    environ.get('QUERY_STRING').split('=', 1)[1]
            # check if file modified since or not
            if environ.get('HTTP_IF_MODIFIED_SINCE') == mtime:
                return HTTP(304, headers=headers).to(environ, start_response)
            headers['Last-Modified'] = mtime
            headers['Pragma'] = 'cache'
            headers['Cache-Control'] = 'private'
            # check whether a range request and serve patial content accordingly
            http_range = environ.get('HTTP_RANGE', None)
            if http_range:
                match = REGEX_RANGE.match(http_range)
                start = match.group('start') or 0
                stop = match.group('stop') or (fsize - 1)
                stream = FileSubset(stream, start, stop + 1)
                headers['Content-Range'] = 'bytes %i-%i/%i' % (start, stop, fsize)
                headers['Content-Length'] = '%i' % (stop - start + 1)
            else:
                headers['Content-Length'] = fsize
            start_response('200 OK', headers.items())
            block_size = GLOBAL['stream_block_size']
            # serve using wsgi.file_wrapper is available
            if 'wsgi.file_wrapper' in environ:
                return environ['wsgi.file_wrapper'](stream, block_size)
            else:
                return iter(lambda: stream.read(block_size), '')
    else:
        # no static file return data as returned by action
        return data


def error_handler(environ, start_response):
    t0 = time.time()
    app = environ['web2py.application'] = (environ.get('PATH_INFO', None) or '/unknown').split('/')[1]
    now = environ['web2py.now'] = datetime.datetime.now()
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


def scan_apps(folder):
    expose.routes_in[:] = []
    for app in os.listdir(folder):
        if os.path.isdir(os.path.join(folder,app)):
            expose.application = app
            expose.prefix = app
            main = os.path.join(folder,app,'main.py')
            if os.path.exists(main):
                fullname = 'apps.%s.main' % app
                logging.info('scanning %s ...' % fullname)
                try:
                    __import__(fullname, globals(), locals(), [], -1)
                except ImportError:
                    logging.error(traceback.format_exc())
                        

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
    scan_apps(GLOBAL['apps_folder'])
    r = Rocket((options.ip, int(options.port)), 'wsgi', {'wsgi_app': error_handler})
    r.start()
