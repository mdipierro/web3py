import os
import re
import glob
import copy
import cStringIO
import cgi
import urllib

from .http import HTTP
from .helpers import TAG, tag, cat, safe, xmlescape
from .storage import Storage
from .template import render
from .current import current

def URL(f,c,a,r=None,args=[],vars={}):
    if f is None:
        f,c,a=f.funciton,r.controller,r.application
    elif c is None:
        c,a=r.controller,r.application
    elif a is None:
        f,c,a=c,f,r.application        
    else:
        f,c,a = a,c,f
    q = urllib.quote
    url = '/%s/%s/%s' % (a,c,f)    
    if args:
        if not isinstance(args,(list,tuple)): args=[args]
        url+='/'+''.join(q(x) for x in args)
    if vars:
        url+='?'+'&'.join('%s=%s' % (q(k),q(v)) for k,v in vars.iteritems())
    return url

class Response(Storage):
    css_template = '<link href="%s" rel="stylesheet" type="text/css" />'                   
    js_template = '<script src="%s" type="text/javascript"></script>'                      

    def __init__(self):
        self.body = cStringIO.StringIO()
        self.files = []
        self.meta = Storage()
        self.delimiters = ('{{','}}')
    def write(self,data,escape=True):
        return self.body.write(data.as_html() if isinstance(data,TAG) else xmlescape(str(data)) if escape else str(data))
    def include_meta(self):                                                            
        s = '\n'.join(                                                                 
            '<meta name="%s" content="%s" />\n' % (k, xmlescape(v))                    
            for k, v in (self.meta or {}).iteritems())                                 
        self.write(s, escape=False)
    def include_files(self):
        s=''
        for item in self.files:
            if isinstance(item, str):
                f = item.lower().split('?')[0]
                if f.endswith('.css'): s += self.css_template % item
                elif f.endswith('.js'): s += self.js_template % item                                            
        self.write(s, escape=False)

def build_environment(current,c,f,e,args):
    a = current.application
    environment = {}
    for name in 'A,B,BODY,BR,CENTER,CLEANUP,CRYPT,DAL,DIV,EM,EMBED,FIELDSET,FORM,H1,H2,H3,H4,H5,H6,HEAD,HR,HTML,I,IFRAME,IMG,INPUT,LABEL,LEGEND,LI,LINK,LOAD,MARKMIN,META,OBJECT,OL,ON,OPTGROUP,OPTION,P,PRE,SCRIPT,SELECT,SPAN,STYLE,TABLE,TBODY,TD,TEXTAREA,TFOOT,TH,THEAD,TITLE,TR,TT,UL'.split(','):
        environment[name] = tag[name]    
    environment['T'] = current.T
    environment['CAT'] = cat
    environment['XML'] = safe
    environment['redirect'] = HTTP.redirect

    environment['request'] = current.request = request = Storage()
    environment['response'] = current.response = response = Response()

    environment['session'] = session = current.session
    environment['URL'] = lambda f=None,c=None,a=None,r=request,args=[],vars={}:URL(f,c,a,r,args,vars)    
    request.env = current.env
    request.now = current.now
    request.application = a
    request.controller = c
    request.function = f
    request.extension = e
    request.args = ListStorage(args)
    request.is_http = current.method == 'https'
    request.client = current.env.remote_addr
    request.cookies = current.request_cookies
    request.get_vars = current.get_vars
    request.post_vars = current.post_vars
    request.vars = copy.copy(current.get_vars)
    request_is_local = True

    # <begin missing stuff>
    response.view = None # should be defined
    environment['MENU'] = lambda *a, **b: 'missing'
    environment['BEAUTIFY'] = lambda *a, **b: 'missing'
    # <end missing stuff>

    for key,value in current.post_vars.iteritems():
        if not key in request.vars:
            request.vars[key] = value
        else:
            if not isinstance(request.vars[key],list):
                request.vars[key] = [request.vars[key]]
            if isinstance(value,list):
                request.vars[key]+=value
            else:
                request.vars[key]+=[value]
    return environment

class ListStorage(list):
    def __call__(self,i):
        return self[i] if i<len(self) else None


def web2py_handler():
    folder = 'apps'+os.sep+current.application
    items = current.path_info.split('/')
    controller = items[2] if len(items)>2 else 'default'
    function = items[3] if len(items)>3 else 'index.html'
    extension = 'html'
    if '.' in function:
        function, extension = function.rsplit('.',1)
    args = items[4:]
    environment = build_environment(current,controller,function,
                                    extension,args)
    old_env = copy.copy(environment)
    for model in sorted(glob.glob(os.path.join(folder,'models','*.py'))):
        execfile(model,environment,{})
    execfile(os.path.join(folder,'controllers',controller+'.py'),environment)
    output = environment[function]()
    if isinstance(output,dict):
        old_env.update(output)
        tpath = os.path.join(folder,'views')
        template = os.path.join(tpath,controller,function+'.'+extension)
        if not os.path.exists(template):            
            template = os.path.join(tpath,'generic.'+extension)
        output = render(filename = template, path = tpath, context = old_env)
    elif isinstance(output,TAG):
        output = output.as_html()
    return output
