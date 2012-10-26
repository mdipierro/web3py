import re
import os
import logging
import urllib
import threading
import traceback

from .cache import cache
from .cleaners import Cleaner, WrapWithCleaners
from .storage import Storage
from .template import render
from .current import current

__all__ = ['expose', 'url']

# global object exposed to apps

class expose(object):
    """
    In apps/myapp/main.py

       @export(path='hello/<str:name>')
       def index(current,name): return 'hello '+name
    
       @export()
       def other(current):
       HTTP.redirect(current.url('index',args='Max'))
    """

    application = ''
    prefix = '/<app>'
    apps = {}
    routes_in = []
    routes_out = {}    
    common_cleaners = []
    REGEX_INT = re.compile('<int\:(\w+)>')
    REGEX_STR = re.compile('<str\:(\w+)>')
    REGEX_ANY = re.compile('<any\:(\w+)>')
    REGEX_ALPHA = re.compile('<str\:(\w+)>')
    REGEX_DATE = re.compile('<date\:(\w+)>')

    @staticmethod
    def build_regex(schemes, hostname, methods, path):
        path = expose.REGEX_INT.sub('(?P<\g<1>>\d+)', path)
        path = expose.REGEX_STR.sub('(?P<\g<1>>[^/]+)', path)
        path = expose.REGEX_ANY.sub('(?P<\g<1>>.*)', path)
        path = expose.REGEX_ALPHA.sub('(?P<\g<1>>\w+)', path)
        path = expose.REGEX_DATE.sub('(?P<\g<1>>\d{4}-\d{2}-\d{2})', path)
        re_schemes = ('|'.join(schemes)).lower()
        re_methods = ('|'.join(methods)).lower()
        re_hostname = re.escape(hostname) if hostname else '[^/]*'
        expr = '^(%s) (%s)\://(%s)(%s)$' % \
            (re_methods, re_schemes, re_hostname, path)
        return expr

    def __init__(self,
                 path = None,
                 name = None,
                 template = None,
                 requires = None,
                 cleaners = None,
                 schemes = None,
                 hostname = None,
                 methods = None,
                 cache = None,
                 cache_expire = 0):
        if callable(path):
            raise SyntaxError('@expose(), not @expose')
        self.schemes = schemes or ('http','https')
        self.methods = methods or ('get','post','head')
        self.hostname = hostname
        self.path = path
        self.name = name
        self.template = template
        self.requires = requires
        self.cache = cache
        self.cache_expire = cache_expire
        self.cleaners = self.common_cleaners + (cleaners or [])
        # check cleaners are indeed valid cleaners
        if any(not isinstance(cleaner, Cleaner) for cleaner in self.cleaners):
            raise RuntimeError('Invalid Cleaner')

    def build_name(self):
        short = self.filename[1+len(self.folder):].rsplit('.',1)[0]
        return '.' + '.'.join(short.split(os.sep) + [self.func_name])

    def __call__(self, func):
        self.application = expose.application
        self.prefix = expose.prefix
        self.func_name = func.__name__
        self.filename = func.__code__.co_filename
        self.mtime = os.path.getmtime(self.filename)
        if not self.path:
            self.path = '/' + func.__name__ + '(.\w+)?'
        if not self.name:
            self.name = self.build_name()
        if not self.path.startswith('/'):
            self.path = '/'+self.path
        if not self.template:
            self.template = self.func_name + '.<ext>'
        if not self.path.startswith('/<app>/'):
            if self.path == '/':
                self.path = self.prefix or '/'
            else:
                self.path = '%s%s' % (self.prefix, self.path)            
        if self.name.startswith('.'):
            self.name = '%s%s' % (self.application, self.name)
        if self.application:
            self.template_path = 'apps/%s/templates/' % self.application
        else:
            raise RuntimeError('unable to determine the application name')
        wrapped_func = WrapWithCleaners(self.cleaners)(func)
        if self.cache_expire > 0:
            self.func = cache(wrapped_func, self.cache_expire,
                              cache_args=False, cache_vars = True)
        else:
            self.func = wrapped_func
        self.regex = expose.build_regex(
            self.schemes, self.hostname, self.methods, self.path)
        route = (re.compile(self.regex), self)
        expose.routes_in.append(route)
        expose.routes_out[self.name] = expose.remove_decoration(self.path)
        if not self.application in expose.apps:
            expose.apps[self.application] = []
        expose.apps[self.application].append(route)
        logging.info("  exposing '%s' as '%s'" % (self.name, self.path))
        return func

    REGEX_DECORATION = re.compile('(([?*+])|(\([^()]*\))|(\[[^\[\]]*\])|(\<[^<>]*\>))')
    REGEX_SLASHES = re.compile('^..*(/+)$')

    @staticmethod
    def remove_decoration(path):
        """
        converts somehing like "/junk/test_args/<str:a>(/<int:b>)?"
        into something like    "/junk/test_args" for reverse routing
        """
        while True:
            new_path = expose.REGEX_DECORATION.sub('',path)
            if new_path == path:
                return expose.REGEX_SLASHES.sub('',path)
            else:
                path = new_path

    @staticmethod
    def clear(application):        
        " remove all routes and reversed routes for this application "
        for route in expose.apps.get(application,[]):
            expose.routes_in.remove(route)
            del expose.routes_out[route[1].name]

    @staticmethod
    def run_dispatcher():        
        " maps the path_info into a function call "
        expression = '%s %s://%s%s' % (
            current.method, current.scheme, current.hostname, current.path_info)
        for regex, obj in expose.routes_in:
            match = regex.match(expression)
            if match:
                current.name = obj.name
                print current.name
                output = obj.func(**match.groupdict())
                break
        else:
            output = 'Invalid action'

        if isinstance(output, str):
            current.output = [output]
        elif isinstance(output, dict):
            if not 'current' in output:
                output['current'] = current
            filename = os.path.join(
                obj.template_path,
                obj.template.replace('<ext>',current.extension))
            if os.path.exists(filename):
                output = render(filename = filename,
                                path = obj.template_path,
                                context = output)
            else:
                output = str(output)
            current.output = [output]
        elif isinstance(output, TAG):
            current.output = [output.as_html()]
        else:
            current.output = output

    @staticmethod
    def scan_apps(folder):
        " loops over existing apps and imports main.py, creates routes "
        for app in os.listdir(folder):
            expose.scan(folder,app)
                            
    @staticmethod
    def scan(folder,app,force_reload=True,lock = threading.RLock()):
        " imports a single app from folder (apps folder) "
        with lock:
            expose.clear(app)
            if os.path.isdir(os.path.join(folder,app)):
                expose.folder = os.path.join(folder,app)
                expose.application = app
                expose.prefix = '/'+app
                main = os.path.join(expose.folder,'main.py')
                if os.path.exists(main):
                    fullname = 'apps.%s.main' % app
                    logging.info('scanning %s ...' % fullname)
                    try:
                        module = __import__(fullname, globals(), locals(), [], -1)
                        if force_reload:
                            reload(module)
                    except ImportError:
                        logging.error(traceback.format_exc())



def url(path, extension = None, args = None, vars = None,
        anchor = None, sign = None, scheme = None, host = None):

    """
    given

        # in file myapp/main.py
        expose.prefix = '/myapp' # set automayically from path
        @expose()
        def index(): return 'test'

    one can refer to the url of index() as

        url('index') # assumes current app and file
        url('.main.index') # makes a guess for myapp prefix
        url('myapp.main.index') # index function in myapp/main.py
        url('./index') # makes a guess for myapp prefix
        url('/myapp/index')

    """
    
    q = urllib.quote
    if not '/' in path:
        if not '.' in path:
            module = current.name.rsplit('.',1)[0]
            path = module +'.'+path
        elif path.startswith('.'):
            path = current.applicatio + path
        try:
            url = expose.routes_out[path]
        except KeyError:
            raise RuntimeError('invalid url("%s",...)' % path)        
    elif path.startswith('./'):
        prefix = expose.apps[current.application][1].prefix
        path = prefix + path[1:]
    if args is not None:
        if not instance(args,(list,tuple)):
            args = (args,)
        url = url + '/' + '/'.join(q(a) for a in args)
    if extension:
        url = url + '.' + extension
    if sign:
        if not vars:
            vars = dict()
        vars['_signature'] = sign(url)
    if vars:
        url = url + '?' + '&'.join('%s=%s' % (q(k),q(v)) for k,v in vars.iteritems())
    if scheme is True:
        scheme = current.scheme
    if scheme:
        host = host or current.hostname
        url = '%s/%s%s' % (scheme, host, url)
    return url
            

# session object

class Session(Storage):
    def __init__(self,current):
        pass
