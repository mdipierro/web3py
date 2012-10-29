from web3py import DAL, Field, expose, tag, cat, safe, HTTP, url, Form, DALForm, current
from web3py.session import SessionCookieManager
from web3py.dal import Transact
from web3py.validators import IS_NOT_EMPTY

db = DAL('sqlite://storage.test')
db.define_table('person',Field('name',requires=IS_NOT_EMPTY()))

expose.common_cleaners = [SessionCookieManager('test'),Transact(db)]

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

@expose()
def counter():
    current.session.counter = (current.session.counter or 0)+1
    return current.session.counter

@expose(template='index.html')
def dal_form():
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
