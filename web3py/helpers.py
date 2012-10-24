import re

from .sanitizer import sanitize
from .storage import Storage

__all__ = ['tag', 'cat', 'safe']

# web2py style helpers

def xmlescape(s, quote=True):
    """
    returns an escaped string of the provided text s

    :param s: the text to be escaped
    :param quote: optional (default False)
    """

    # first try the as_html function
    if isinstance(s, TAG):
        return s.as_html()

    # otherwise, make it a string
    if not isinstance(s, (str, unicode)):
        s = str(s)
    elif isinstance(s, unicode):
        s = s.encode('utf8', 'xmlcharrefreplace')

    s = s.replace("&", "&amp;") # Must be done first!
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    s = s.replace("'", "&#x27;")
    if quote:
        s = s.replace('"', "&quot;")
    return s


class TAG(object):
    def __init__(self, name):
        self.safe = safe
        self.name = name
        self.parent = None

    def __call__(self, *components, **attributes):
        self.components = list(components)
        self.attributes = attributes
        for component in self.components:
            if isinstance(component,TAG):
                component.parent = self
        return self

    def append(self,component):
        self.components.append(component)

    def insert(self,i,component):
        self.components.insert(i,component)
        
    def remove(self,component):
        self.components.remove(component)

    def __getitem__(self,key):
        if isinstance(key,int):
            return self.components[key]
        else:
            return self.attributes.get(key)

    def __setitem__(self,key,value):
        if isinstance(key,int):
            self.components.insert(key,value)
        else:
            self.attributes[key] = value
    
    def __iter__(self):
        for item in self.components:
            yield item

    def __str__(self):
        return self.as_html()

    def add_class(self, name):
        """ add a class to _class attribute """
        c = self['_class']
        classes = (set(c.split()) if c else set()) | set(name.split())
        self['_class'] = ' '.join(classes) if classes else None
        return self

    def remove_class(self, name):
        """ remove a class from _class attribute """
        c = self['_class']
        classes = (set(c.split()) if c else set()) - set(name.split())
        self['_class'] = ' '.join(classes) if classes else None
        return self

    regex_tag = re.compile('^([\w\-\:]+)')
    regex_id = re.compile('#([\w\-]+)')
    regex_class = re.compile('\.([\w\-]+)')
    regex_attr = re.compile('\[([\w\-\:]+)=(.*?)\]')

    def find(self,expr):
        union = lambda a,b: a.union(b)        
        if ',' in expr:
            tags = reduce(union, [self.find(x.strip()) for x in expr.split(',')],set())
        elif ' ' in expr:
            tags = [self]
            for k,item in enumerate(expr.split()):
                if k>0:
                    children = [set([c for c in tag if isinstance(c,TAG)]) for tag in tags]
                    tags = reduce(union,children)
                tags = reduce(union, [tag.find(item) for tag in tags],set())
        else:
            tags = reduce(union,[c.find(expr) for c in self if isinstance(c,TAG)],set())
            tag = TAG.regex_tag.match(expr)
            id = TAG.regex_id.match(expr)
            _class = TAG.regex_class.match(expr)
            attr = TAG.regex_attr.match(expr)
            if \
                    (tag is None or self.name == tag.group(1)) and \
                    (id is None or self['_id'] == id.group(1)) and \
                    (_class is None or _class.group(1) in (self['_class'] or '').split()) and \
                    (attr is None or self['_'+attr.group(1)] == attr.group(2)):
                tags.add(self)
        return tags

    def as_html(self):
        name = self.name
        co = ''.join(xmlescape(v) for v in self.components)
        ca = ' '.join('%s="%s"' % (k[1:], k[1:] if v==True else xmlescape(v))
             for (k, v) in sorted(self.attributes.items())
             if k.startswith('_') and v is not None)
        ca = ' ' + ca if ca else ''
        if not self.components:
            return '<%s%s />' % (name, ca)
        else:
            return '<%s%s>%s</%s>' % (name, ca, co, name)

    __repr__ = __str__


class METATAG(object):
    def __getattr__(self, name):
        return TAG(name)

    def __getitem__(self, name):
        return TAG(name)

tag = METATAG()

class cat(TAG):
    def __init__(self, *components):
        self.components = components

    def as_html(self):
        return ''.join(xmlescape(v) for v in self.components)

class safe(TAG):
    def __init__(self, text, sanitize=False, allowed_tags={}):
        self.text = text
        self.allowed_tags = allowed_tags

    def as_html(self):
        return sanitize(self.text, self.allowed_tags.keys(), self.allowed_tags)
