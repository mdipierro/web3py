from web3py import expose, run, tag, cat, safe, HTTP, DAL, Field, Form

db = DAL('sqlite://storage.test')
db.define_table('junk',Field('ts'))

@expose('/index')
def index(current):
    return 'hello world'

@expose('/test_args/<str:a>/<int:b>?')
def test_args(current,a,b=9):
    return repr(dict(a=a,b=b))

@expose()
def test_template(current):
    return dict(message='test_template')

@expose(dbs=[db])
def test_database(current):
    db._adapter.reconnect()
    db.junk.insert(ts=current.now)
    db.commit()
    return str(db(db.junk).select())

@expose()
def test_helpers(current):
    return tag.html(tag.body(tag.h1(cat('hello', 'world'), safe('<span>test</span>'), _style='color:red')))

@expose('/doh')
def test(current):
    1 / 0
    return 'hello world'

@expose()
def test_form(current):
    message = current.post_vars.name or 'None'
    form = Form(Field('name'))
    return '<html><body>%s<hr>%s</body></html>' % (message, form)
    

@expose()
def test_redirect(current):
    current.redirect('/index')


