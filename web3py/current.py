import os
import cgi
import logging
import cgi
import platform
import urllib

from .storage import Storage
from .contenttype import contenttype
from .utils import secure_loads, secure_dumps
from .languages import translator
from .expose import expose

if platform.python_version()[0] == '3':
    from http.cookies import SimpleCookie # python 3
else:
    from Cookie import SimpleCookie # python 2

__all__ = ['Current']

# global object exposed to apps

class Current(object):

    def __init__(self,environ):
        self.environ = environ
        self.status_code = 200    
        self.scheme = 'https' if \
            environ.get('wsgi.url_scheme','').lower() == 'https' or \
            environ.get('HTTP_X_FORWARDED_PROTO','').lower() == 'https' or \
            environ.get('HTTPS','') == 'on' else 'http'
        self.name = '<app>.<main>.<func>' # defined in expose.run
        self.hostname = environ['HTTP_HOST']
        self.method = environ.get('HTTP_METHOD', 'get').lower()
        self.path_info = environ['PATH_INFO']
        self.input = environ.get('wsgi.input')
        self.now = environ['w3p.now']
        self.application = environ['w3p.application']
        self.extension = (self.path_info.rsplit('.',1)+['html'])[1]
        self.response_cookies = SimpleCookie()
        self.response_headers = {'Content-Type':contenttype(self.path_info,'text/html')}
        # lazy attributes
        self._get_vars = None
        self._post_vars = None
        self._cache = None
        self._session = None
        self._request_cookies = None
        self._t = None
        self._env = None

    def _parse_get_vars(self):
        query_string = self.environ.get('QUERY_STRING','')
        dget = cgi.parse_qs(query_string, keep_blank_values=1)
        get_vars = self._get_vars = Storage(dget)
        for (key, value) in get_vars.iteritems():
            if isinstance(value,list) and len(value)==1:
                get_vars[key] = value[0]

    def _parse_post_vars(self):
        environ = self.environ
        post_vars = self._post_vars = Storage()
        length = environ.get('CONTENT_LENGTH')        
        if self.input and environ.get('REQUEST_METHOD') in ('POST', 'PUT', 'BOTH'):
            dpost = cgi.FieldStorage(fp=self.input, environ=environ, keep_blank_values=1)
            for key in sorted(dpost):
                dpk = dpost[key]
                if not isinstance(dpk, list):
                    dpk = [dpk]
                dpk = [item.value if not item.filename else item for item in dpk]
                post_vars[key] = dpk
            for (key,value) in self._post_vars.iteritems():
                if isinstance(value,list) and len(value)==1:
                    post_vars[key] = value[0]

    @property
    def get_vars(self):       
        " lazily parse the query string into get_vars "
        if self._get_vars is None:
            self._parse_get_vars()
        return self._get_vars
    @property
    def post_vars(self):
        " lazily parse the request body into post_vars "
        if self._post_vars is None:
            self._parse_post_vars()
        return self._post_vars
    @property
    def env(self):
        " lazily parse the invironment variables into a storage, for backward compatibility, it is slow "
        self._env = self._env or Storage((k.lower().replace('.','_'),v) for (k,v) in self.environ.iteritems())
        return self._env
    @property
    def session(self):
        " lazily create the session "
        if self._session is None:
            self._session = Session(self)
        return self._session
    @property
    def request_cookies(self):       
        " lazily parse the request cookies "
        if self._request_cookies is None:
            self._request_cookies = SimpleCookie()
            self._request_cookies.load(self.environ.get('HTTP_COOKIE',''))
        return self._request_cookies
    @property
    def T(self):
        " lazily allocate the T object "
        if self._t is None:
            self._t = translator(os.path.join('apps',self.application,'languages'),
                                 self.environ.get('HTTP_ACCEPT_LANGUAGE'))
        return self._t

    def url(self,path,extension=None,args=None,vars=None,anchor=None,sign=None,scheme=None,host=None):
        q = urllib.quote
        if not '.' in path:
            path = self.name.rsplit('.',1)[0]+'.'+path
        elif path.startswith('.'):
            path = self.application + path
        try:
            url = expose.routes_out[path]
        except KeyError:
            raise RuntimeError('invalid url("%s",...)' % path)        
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
            scheme = self.scheme
        if scheme:
            host = host or self.hostname
            url = '%s/%s%s' % (scheme, host, url)
        return url
            

# session object

class Session(Storage):
    def __init__(self,current):
        pass
