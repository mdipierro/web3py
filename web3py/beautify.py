import cgi
import copy
from .helpers import TAG, tag

__all__ = ['BEAUTIFY']

class BEAUTIFY(TAG):

    """
    example::

        >>> BEAUTIFY(['a', 'b', {'hello': 'world'}]).as_html()
        '<div><table><tr><td><div>a</div></td></tr><tr><td><div>b</div></td></tr><tr><td><div><table><tr><td style="font-weight:bold;vertical-align:top">hello</td><td valign="top">:</td><td><div>world</div></td></tr></table></div></td></tr></table></div>'

    turns any list, dictionary, etc into decent looking html.
    Two special attributes are
    :sorted: a function that takes the dict and returned sorted keys
    :keyfilter: a funciton that takes a key and returns its representation
                or None if the key is to be skipped. By default key[:1]=='_' is skipped.
    """

    @staticmethod
    def no_underscore(key):
        if key[:1] == '_':
            return None
        return key

    def __init__(self, component, **attributes):
        TAG.__init__(self,'DIV')
        self.components = [component]
        self.attributes = attributes
        sorter = attributes.get('sorted', sorted)
        keyfilter = attributes.get('keyfilter', BEAUTIFY.no_underscore)
        components = []
        attributes = copy.copy(self.attributes)
        level = attributes['level'] = attributes.get('level', 6) - 1
        if '_class' in attributes:
            attributes['_class'] += 'i'
        if level == 0:
            return
        for c in self.components:
            if hasattr(c, 'value') and not callable(c.value):
                if c.value:
                    components.append(c.value)
            if isinstance(c,TAG):
                components.append(c)
                continue
            elif hasattr(c, 'keys') and callable(c.keys):
                rows = []
                try:
                    keys = (sorter and sorter(c)) or c
                    for key in keys:
                        if isinstance(key, (str, unicode)) and keyfilter:
                            filtered_key = keyfilter(key)
                        else:
                            filtered_key = str(key)
                        if filtered_key is None:
                            continue
                        value = c[key]
                        if isinstance(value, types.LambdaType):
                            continue
                        rows.append(
                            tag.TR(
                                tag.TD(filtered_key, _style='font-weight:bold;vertical-align:top'),
                                tag.TD(':', _valign='top'),
                                tag.TD(BEAUTIFY(value, **attributes))))
                    components.append(tag.TABLE(*rows, **attributes))
                    continue
                except:
                    pass
            if isinstance(c, str):
                components.append(str(c))
            elif isinstance(c, unicode):
                components.append(c.encode('utf8'))
            elif isinstance(c, (list, tuple)):
                items = [tag.TR(tag.TD(BEAUTIFY(item, **attributes)))
                         for item in c]
                components.append(tag.TABLE(*items, **attributes))
            elif isinstance(c, cgi.FieldStorage):
                components.append('FieldStorage object')
            else:
                components.append(repr(c))
        self.components = components

