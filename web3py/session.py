from .utils import secure_loads, secure_dumps
from .cleaners import Cleaner
from .current import current
from .storage import Storage

class SessionCookieManager(Cleaner):
    def __init__(self,key):
        self.key = key
    def on_start(self):
        self.cookie_data_name = 'w3p_session_data_%s' % current.application
        request_cookies = current.request_cookies
        if self.cookie_data_name in request_cookies:
            cookie_data = request_cookies[self.cookie_data_name].value
            current.session = secure_loads(cookie_data,self.key)
        if not current.session:
            current.session = Storage()
    def on_success(self):
        current.response_cookies[self.cookie_data_name] = secure_dumps(
            current.session,self.key)
    def on_failure(self):
        pass
