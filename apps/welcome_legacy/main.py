import os
import re
import glob
import copy
import cStringIO
import cgi

from web3py import tag, cat, safe, HTTP, expose
from web3py.helpers import TAG
from web3py.storage import Storage
from web3py.template import render
path = os.path.dirname(__file__)

def build_environment(current,c,f,e,args):
    a = current.application
    environment = {}
    for name in 'A,B,BODY,BR,CENTER,CLEANUP,CRYPT,DAL,DIV,EM,EMBED,FIELDSET,FORM,H1,H2,H3,H4,H5,H6,HEAD,HR,HTML,I,IFRAME,IMG,INPUT,LABEL,LEGEND,LI,LINK,LOAD,MARKMIN,META,OBJECT,OL,ON,OPTGROUP,OPTION,P,PRE,SCRIPT,SELECT,SPAN,STYLE,TABLE,TBODY,TD,TEXTAREA,TFOOT,TH,THEAD,TITLE,TR,TT,UL'.split(','):
        environment[name] = tag[name]    
    environment['MENU'] = lambda *a, **b: 'missing'
    environment['BEAUTIFY'] = lambda *a, **b: 'missing'
    environment['T'] = current.T
    environment['CAT'] = cat
    environment['XML'] = safe
    environment['redirect'] = HTTP.redirect
    environment['URL'] = lambda c=c,f=f,a=a,r=None,args=[],vars={}: \
        '/%s/%s/%s/%s' % (a,c,f,''.join(args))
    environment['request'] = request = Storage()
    environment['response'] = response = Storage()
    environment['session'] = session = Storage()
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
    response.files = []
    response.meta = Storage()
    response.view = None # should be defined
    response.delimiters = ('{{','}}')
    response.body = cStringIO.StringIO()
    response.write = lambda data,escape=True,b=response.body: b.write(data.as_html() if isinstance(data,TAG) else cgi.escape(str(data)) if escape else str(data))
    response.include_files = lambda *a,**b: 'missing'
    response.include_meta = lambda *a,**b: 'missing'
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
        
PATH_REGEX = re.compile('(/[^/]+)+')

@expose(path='/(.*)')
def backward_compatibility_action(current):
    folder = 'apps'+os.sep+current.application
    if PATH_REGEX.match(current.path_info):
        items = current.path_info.split('/')
        controller = items[2] if len(items)>2 else 'default'
        function = items[3] if len(items)>3 else 'index.html'
        extension = 'html'
        if '.' in function:
            function, extension = function.rsplit('.',1)
        args = items[4:]
    environment = build_environment(current,controller,function,extension,args)
    old_env = copy.copy(environment)
    for model in sorted(glob.glob(os.path.join(folder,'models','*.py'))):
        print model
        execfile(model,environment,{})
    execfile(os.path.join(folder,'controllers',controller+'.py'),environment)
    output = environment[function]()
    if isinstance(output,dict):
        old_env.update(output)
        tpath = os.path.join(folder,'views')
        template = os.path.join(tpath,controller,function+'.'+extension)
        if not os.path.exists(template):
            template = os.path.join(tpath,'generic.'+extension)
        output = str(output) #render(filename=template,path=tpath,context=old_env)
    elif isinstance(output,TAG):
        output = output.as_html()
    print output
    return output
