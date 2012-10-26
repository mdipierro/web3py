from web3py import *
from web3py.session import SessionCookieManager
from web3py.validators import IS_NOT_EMPTY

db = DAL('sqlite://storage.test')
db.define_table('person',Field('name',requires=IS_NOT_EMPTY()))

class Example(Cleaner):
    def __init__(self): pass
    def on_start(self): print 'start'
    def on_success(self): print 'success'
    def on_failure(self): print 'failure'
expose.common_cleaners = [Example(), SessionCookieManager(), db]

@expose()
def index():
    form = Form(Field('name',requires=IS_NOT_EMPTY()),
                Field('area','text'),
                Field('check','boolean',default=True),
                Field('age','integer',comment='Try type in a number!'),
                Field('weight','double'),
                Field('a','time'),
                Field('b','date'),
                Field('c','datetime')).process()
    message = form.vars.name or ''
    return locals()

@expose()
def error():
    return 1/0
    

@expose(template='index.html')
def index1():
    form = DALForm(db.person, record_id=1).process()
    db.commit()
    message = form.vars.name
    return locals()

@expose(cache_expire=10)
def timer():
    import time
    return time.ctime()

@expose()
def try_redirect1():
    HTTP.redirect(url('welcome.main.index'))

@expose()
def try_redirect2():
    HTTP.redirect(url('.main.index'))

@expose()
def try_redirect3():
    HTTP.redirect(url('index'))
