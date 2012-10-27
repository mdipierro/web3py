import re

from .sanitizer import sanitize
from .storage import Storage

__all__ = ['tag', 'cat', 'safe']

# web2py style helpers

def xmlescape(s, quote=True):
    """
    returns an escaped string of the provided text s
    s: the text to be escaped
    quote: optional (default True)
    """
    # first try the xml function
    if isinstance(s, TAG):
        return s.xml()
    # otherwise, make it a string
    if not isinstance(s, (str, unicode)):
        s = str(s)
    elif isinstance(s, unicode):
        s = s.encode('utf8', 'xmlcharrefreplace')
    s = s.replace("&", "&amp;") # Must be done first!
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    if quote:
        s = s.replace("'", "&#x27;")
        s = s.replace('"', "&quot;")
    return s


class TAG(object):

    rules = {'ul':['li'], 
             'ol':['li'], 
             'table':['tr','thead','tbody'], 
             'thead':['tr'],
             'tbody':['tr'],
             'tr':['td','th'],
             'select',['option','optgroup'],
             'optgroup':['optionp']}
    
    def __init__(self, name):
        self.safe = safe
        self.name = name
        self.parent = None
        self.components = []
        self.attributes = {}        

    @staticmethod
    def wrap(component,rules):
        if not rules:
            return component
        if not isinstance(component,TAG) or not component.name in rules:
            return TAG(rules[0])(component)

    def __call__(self, *components, **attributes):
        rules = self.rules.get(self.name,[])
        self.components = [self.wrap(comp,rules) for comp in components]
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
        return self.xml()
    
    def __add__(self,other):
        return cat(self,other)

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
            tags = reduce(union, [self.find(x.strip()) 
                                  for x in expr.split(',')],set())
        elif ' ' in expr:
            tags = [self]
            for k,item in enumerate(expr.split()):
                if k>0:
                    children = [set([c for c in tag if isinstance(c,TAG)]) 
                                for tag in tags]
                    tags = reduce(union,children)
                tags = reduce(union, [tag.find(item) for tag in tags],set())
        else:
            tags = reduce(union,[c.find(expr) 
                                 for c in self if isinstance(c,TAG)],set())
            tag = TAG.regex_tag.match(expr)
            id = TAG.regex_id.match(expr)
            _class = TAG.regex_class.match(expr)
            attr = TAG.regex_attr.match(expr)
            if (tag is None or self.name == tag.group(1)) and \
               (id is None or self['_id'] == id.group(1)) and \
               (_class is None or _class.group(1) in \
                    (self['_class'] or '').split()) and \
               (attr is None or self['_'+attr.group(1)] == attr.group(2)):
                tags.add(self)
        return tags

    def xml(self):
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
    as_html = xml # compatibility layer

class METATAG(object):

    def __getattr__(self, name):
        return TAG(name)

    def __getitem__(self, name):
        return TAG(name)

tag = METATAG()

class cat(TAG):

    def __init__(self, *components):
        self.components = components

    def xml(self):
        return ''.join(xmlescape(v) for v in self.components)

class safe(TAG):

    default_allowed_tags = {
        'a':['href','title','target'], 'b':[], 'blockquote':['type'],
        'br':[], 'i':[], 'li':[], 'ol':[], 'ul':[], 'p':[], 'cite':[],
        'code':[], 'pre':[], 'img':['src', 'alt'], 'strong':[],
        'h1':[], 'h2':[], 'h3':[], 'h4':[], 'h5':[], 'h6':[],
        'table':[], 'tr':[], 'td':['colspan'], 'div':[],
        }

    def __init__(self, text, sanitize=False, allowed_tags=None):
        self.text = text
        self.allowed_tags = allowed_tags or safe.default_allowed_tags

    def xml(self):
        return self.text if not sanitize else \
            sanitize(self.text, self.allowed_tags.keys(), self.allowed_tags)
