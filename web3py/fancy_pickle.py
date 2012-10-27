try:
    from cStringIO import StringIO # python 3
    from cPickle import Pickler, Unpickler, UnpicklingError
except ImportError:
    from io import StringIO # python 2
    from pickle import Pickler, Unpickler, UnpicklingError
    long, str, unicode = int, bytes, str

__all__ = ['load','loads','dump','dumps']

KEY = 'unpickled-object:'

def persistent_id(obj):
    if not isinstance(obj,(int,long,str,unicode,list,tuple,dict)):
        return KEY + repr(obj)
    else:
        return None

def persistent_load(persid):
    if persid.startswith(KEY):
        value = persid[len(KEY):]
        return value
    else:
        raise UnpicklingError('Invalid persistent id')

def dump(data,stream):
    p = Pickler(stream)
    p.persistent_id = persistent_id
    p.dump(data)

def dumps(data):
    stream = StringIO()
    dump(data,stream)
    return stream.getvalue()

def load(stream):
    p = Unpickler(stream)
    p.persistent_load = persistent_load
    return p.load()

def loads(s):
    return load(StringIO(s))

def check():
    a = {'this':'is', 'a':lambda: 'test'}
    s = dumps(a)
    b = loads(s)
    assert "{'this': 'is', 'a': '<function <lambda> at 0x" in repr(b)

check()
