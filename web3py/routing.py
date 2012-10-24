import re
import os
import logging

from .cache import cache
from .template import render

__all__ = ['expose']

# global object exposed to apps

class expose(object):
    application = ''
    prefix = ''
    routes_in = []
    routes_out = []
    REGEX_INT = re.compile('<int\:(\w+)>')
    REGEX_STR = re.compile('<str\:(\w+)>')
    REGEX_ANY = re.compile('<any\:(\w+)>')
    REGEX_ALPHA = re.compile('<str\:(\w+)>')
    REGEX_DATE = re.compile('<date\:(\w+)>')

    @staticmethod
    def build_regex(schemes, hostname, methods, path_info):
        path_info = expose.REGEX_INT.sub('(?P<\g<1>>\d+)', path_info)
        path_info = expose.REGEX_STR.sub('(?P<\g<1>>[^/]+)', path_info)
        path_info = expose.REGEX_ANY.sub('(?P<\g<1>>.*)', path_info)
        path_info = expose.REGEX_ALPHA.sub('(?P<\g<1>>\w+)', path_info)
        path_info = expose.REGEX_DATE.sub(
            '(?P<\g<1>>\d{2}/\d{2}/\d{4})', path_info)
        re_schemes = ('|'.join(schemes)).upper()
        re_methods = ('|'.join(methods)).upper()
        re_hostname = re.escape(hostname) if hostname else '[^/]*'
        return '^(%s)/(%s)/(%s) %s$' % (re_schemes, re_hostname, re_methods, path_info)

    def __init__(self,
                 path_info = None,
                 template = None,
                 requires = None,
                 dbs = None,
                 schemes = None,
                 hostname = None,
                 methods = None,
                 cache = None,
                 cache_expire = 0.5):
        if callable(path_info):
            raise SyntaxError('@expose(), not @expose')
        self.schemes = schemes or ('HTTP', 'HTTPS')
        self.methods = methods or ('GET', 'POST', 'HEAD')
        self.hostname = hostname
        self.path_info = path_info
        self.template = template
        self.requires = requires
        self.dbs = dbs or []
        self.cache = cache
        self.cache_expire = cache_expire

    def __call__(self, func):
        if not self.path_info:
            self.path_info = '/'+func.__name__
        if not self.template:
            self.template = func.__name__ + '.<ext>'
        if self.prefix:
            self.path_info = '/%s%s' % (self.prefix, self.path_info)
        if self.application:        
            self.template_path = 'apps/%s/templates/' % self.application
        else:
            self.path_info = self.path_info.replace('<app>','')
        logging.info('    exposing %s' % self.path_info)
        if self.cache_expire is not 0:
            self.func = cache(func, self.cache_expire,
                              cache_args=False, cache_vars = True)
        else:
            self.func = func
        self.regex = expose.build_regex(
            self.schemes, self.hostname, self.methods, self.path_info)
        expose.routes_in.append((re.compile(self.regex), self))
        return func

    @staticmethod
    def run(current):
        expression = '%s/%s/%s %s' % (
            current.scheme, current.hostname, current.method, current.path_info)
        for regex, obj in expose.routes_in:
            match = regex.match(expression)
            if match:
                output = obj.func(current,**match.groupdict())
                break
        else:
            output = 'Invalid action'
        if isinstance(output, str):
            return [output]
        elif isinstance(output, dict):
            if not 'current' in output:
                output['current'] = current
            output = render(
                filename = os.path.join(
                    obj.template_path,
                    obj.template.replace('<ext>',current.extension)),
                path=obj.template_path,
                context=output)
            return [output]
        elif isinstance(output, TAG):
            return [output.as_html()]
        else:
            return output
