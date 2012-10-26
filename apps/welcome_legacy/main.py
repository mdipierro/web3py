from web3py.expose import expose
from web3py.web2py import web2py_handler
from web3py.session import SessionCookieManager

@expose(path='/(.*)', cleaners = [SessionCookieManager('test')])
def handler():
    return web2py_handler()
