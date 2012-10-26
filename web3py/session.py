from .utils import secure_loads, secure_dumps
from .cleaners import Cleaner
from .current import current
from .storage import Storage

session = Storage()

class SessionCookieManager(Cleaner):
    def on_start(self):
        current.session = session
        pass
    def on_success(self):
        pass
    def on_failure(self):        
        pass
