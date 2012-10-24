import sys
import time
import heapq
import threading

__all__ = ['cache']

class HeapElement(object):

    def __init__(self, expiration, key):
        self.expiration = expiration
        self.key = key

    def __cmp__(self, other):
        return cmp(self.expiration, self.expiration)


class DictElement(object):

    def __init__(self, value, heap_element):
        self.value = value
        self.heap_element = heap_element


class CacheInRam(object):
    """
    Main cache interface

       value = CacheInRam('prefix')(key, func, dt)

    returns func() is data not in cache or stored more then dt seconds ago
    else retrieves the value from cache:

    dt is in seconds
    dt==0 forces value to recompute and store
    dt==None stores the value forever 
    """


    lock = threading.RLock()
    map = {}
    heap = []

    def __init__(self, prefix = ''):
        self.prefix = prefix

    def __call__(self, key, function=lambda:None, dt=None):
        key = self.prefix + key
        now = time.time()
        if dt is None:
            dt = 1000000000
        self.clear(key if dt is 0 else None, now)
        if function:
            expiration = now + dt
            try:
                with CacheInRam.lock:
                    item = self.map[key]
                    self.heap.remove(item.heap_element)
                    item.heap_element.expiration = expiration
                    heapq.heappush(self.heap, item.heap_element)
                return item.value
            except KeyError:
                value = function()
                with CacheInRam.lock:
                    heap_element = HeapElement(expiration, key)
                    heapq.heappush(self.heap, heap_element)
                    self.map[key] = DictElement(value, heap_element)
            return value
        return None

    def clear(self, key=None, now=None):
        now = now or time.time()
        heap = self.heap
        with CacheInRam.lock:
            while heap and heap[0].expiration < now:
                del self.map[heapq.heappop(heap).key]
            if key is not None:
                key = self.prefix + key
                try:
                    e = self.map[key]
                    heap.remove(e.head_element)
                    del self.map[key]
                except KeyError:
                    pass

    def increase(self, key, value):
        key = self.prefix + key
        try:
            with CacheInRam.lock:
                self.map[key].value += value
        except KeyError:
            self(key, lambda: value, None)

CACHE_IN_RAM = CacheInRam()

class cache(object):
    def __init__(self, func, dt, key=None, cache=None, cache_args = True, cache_vars = False):
        self.cache = cache or CACHE_IN_RAM
        self.key = key or func.__code__.co_filename
        self.func = func
        self.dt = dt
        self.cache_args = cache_args
        self.cache_vars = cache_vars
    def __call__(self,*a,**b):
        extra = ''
        if self.cache_args:
            extra += ':%s' % repr(a)
        if self.cache_vars:
            extra += ':%s' % repr(b)
            print self.key+extra, self.dt
        func = lambda a=a,b=b: self.func(*a,**b)
        return self.cache(self.key + extra, func, self.dt)

def example():
    c = CacheInRam()
    sys.stdout.write(c('key', lambda: time.ctime(), 1)+'\n')
    sys.stdout.write(c('key', lambda: time.ctime(), 1)+'\n')
    time.sleep(2)
    sys.stdout.write(c('key', lambda: time.ctime(), 1)+'\n')
    sys.stdout.write(c('key', lambda: time.ctime(), 1)+'\n')

if __name__=='__main__':
    example()
