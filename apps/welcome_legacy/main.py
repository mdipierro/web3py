from web3py.expose import expose
from web3py.web2py import web2py_handler

@expose(path='/(.*)')
def handler():
    return web2py_handler()
