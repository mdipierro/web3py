import sys
import inspect
import traceback

__all__ = ['Cleaner', 'WrapWithCleaners']

class Cleaner(object):
    def on_start(self): pass
    def on_success(self): pass
    def on_failure(self): pass
    def wrap_call(self,func): return func

class WrapWithCleaners(object):
    def __init__(self, cleaners=[]):
        self.cleaners = cleaners
    def __call__(self, f):
        def wrap(f, cleaner):
            def g(*a,**b):
                try:
                    cleaner.on_start()
                    output = cleaner.wrap_call(f)(*a,**b)
                    cleaner.on_success()
                    return output
                except:
                    cleaner.on_failure()
                    raise
            return g
        for cleaner in self.cleaners:
            if isinstance(cleaner,Cleaner):
                f = wrap(f, cleaner)
        return f

def smart_traceback():
    tb = traceback.format_exc()
    frames = []
    for item in inspect.trace():
        frame = item[0]
        try:
            with open(frame.f_code.co_filename,'rb') as file:
                content = file.read()
        except IOError:
            content = '<unavailable>'
        frames.append(dict(filename = frame.f_code.co_filename,
                           content = content,
                           line_number = frame.f_lineno,
                           locals_variables = frame.f_locals,
                           global_variables = frame.f_globals))
    return (tb, frames)

def example():

    class CleanerExample(Cleaner):
        def __init__(self): sys.stdout.write('connecting\n')
        def on_start(self): sys.stdout.write('pool connection\n')
        def on_success(self): sys.stdout.write('commit\n')
        def on_failure(self): sys.stdout.write('rollback\n')
        def insert(self,**data): sys.stdout.write('inserting %s\n' % data)

    db = CleanerExample()

    @WrapWithCleaners((db,))
    def action(x):
        db.insert(key=1/x)
        return

    try:
        a = action(1)
        a = action(0)
    except:
        pass # print smart_traceback()[1][-1]
