from .helpers import TAG, tag, cat

__all__ = ['MENU']

class MENU(TAG):
    """
    Used to build menus

    Optional arguments
      _class: defaults to 'web2py-menu web2py-menu-vertical'
      ul_class: defaults to 'web2py-menu-vertical'
      li_class: defaults to 'web2py-menu-expand'

    Example:
        menu = MENU([['name', False, URL(...), [submenu]], ...])
        {{=menu}}
    """

    def __init__(self, data, **args):
        TAG.__init__(self, 'UL')
        self.data = data
        self.attributes = args
        self.components = []
        if not '_class' in self.attributes:
            self['_class'] = 'web2py-menu web2py-menu-vertical'
        if not 'ul_class' in self.attributes:
            self['ul_class'] = 'web2py-menu-vertical'
        if not 'li_class' in self.attributes:
            self['li_class'] = 'web2py-menu-expand'
        if not 'li_active' in self.attributes:
            self['li_active'] = 'web2py-menu-active'
        if not 'mobile' in self.attributes:
            self['mobile'] = False

    def serialize(self, data, level=0):
        if level == 0:
            ul = tag.UL(**self.attributes)
        else:
            ul = tag.UL(_class=self['ul_class'])
        for item in data:
            (name, active, link) = item[:3]
            if isinstance(link, TAG):
                li = tag.LI(link)
            elif 'no_link_url' in self.attributes and self['no_link_url'] == link:
                li = tag.LI(tag.DIV(name))
            elif link:
                li = tag.LI(tag.A(name, _href=link))
            elif not link and isinstance(name, TAG) and name.name.lower()=='a':
                li = tag.LI(name)
            else:
                li = tag.LI(tag.A(name, _href='#',
                                  _onclick='javascript:void(0);return false;'))
            if len(item) > 3 and item[3]:
                li['_class'] = self['li_class']
                li.append(self.serialize(item[3], level + 1))
            if active or ('active_url' in self.attributes and self['active_url'] == link):
                if li['_class']:
                    li['_class'] = li['_class'] + ' ' + self['li_active']
                else:
                    li['_class'] = self['li_active']
            if len(item) <= 4 or item[4] == True:
                ul.append(li)
        return ul

    def serialize_mobile(self, data, select=None, prefix=''):
        if not select:
            select = tag.SELECT(**self.attributes)
        for item in data:
            if len(item) <= 4 or item[4] == True:
                select.append(tag.OPTION(cat(prefix, item[0]),
                                     _value=item[2], _selected=item[1]))
                if len(item) > 3 and len(item[3]):
                    self.serialize_mobile(
                        item[3], select, prefix=cat(prefix, item[0], '/'))
        select['_onchange'] = 'window.location=this.value'
        return select

    def as_html(self):
        if self['mobile']:
            return self.serialize_mobile(self.data, 0).as_html()
        else:
            return self.serialize(self.data, 0).as_html()
