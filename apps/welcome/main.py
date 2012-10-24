from web3py import *
from web3py.validators import IS_NOT_EMPTY

db = DAL('sqlite://storage.test')
db.define_table('person',Field('name',requires=IS_NOT_EMPTY()))

@expose()
def index(current):
    form = Form(Field('name',requires=IS_NOT_EMPTY()),
                Field('area','text'),
                Field('check','boolean',default=True),
                Field('age','integer',comment='Try type in a number!'),
                Field('weight','double'),
                Field('a','time'),
                Field('b','date'),
                Field('c','datetime')).process(current)
    message = form.vars.name or ''
    return locals()

@expose(template='index.html')
def index1(current):
    form = DALForm(db.person, record_id=1).process(current)
    db.commit()
    message = form.vars.name
    return locals()

@expose(cache_expire=10)
def timer(current):
    import time
    return time.ctime()
