from .utils import secure_loads, secure_dumps
from .cleaners import Cleaner
from .current import current
from .storage import Storage

class SessionCookieManager(Cleaner):
    def __init__(self,key):
        self.key = key
    def on_start(self):
        request = current.request
        self.cookie_data_name = 'w3p_session_data_%s' % request.application
        if self.cookie_data_name in request.cookies:
            cookie_data = request.cookies[self.cookie_data_name].value
            current.session = secure_loads(cookie_data,self.key)
        if not current.session:
            current.session = Storage()
    def on_success(self):
        data = secure_dumps(current.session,self.key)
        current.response.cookies[self.cookie_data_name] = data
    def on_failure(self):
        pass
