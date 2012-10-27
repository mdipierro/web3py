import uuid
import hashlib

from .helpers import tag, TAG
from .storage import Storage
from .current import current

__all__ = ['Form','DALForm']

class Form(TAG):

    @staticmethod
    def widget_string(name,value,_class='string',_id=None):
        return tag.input(_type='text',_name=name,_value=value or '',
                         _class=_class,_id=_id)

    @staticmethod
    def widget_text(name,value,_class='text',_id=None):
        return tag.textarea(value or '',_name=name,
                            _class=_class,_id=_id)

    @staticmethod
    def widget_integer(name,value,_class='integer',_id=None):
        return Form.widget_string(name,value,_class,_id)

    @staticmethod
    def widget_double(name,value,_class='double',_id=None):
        return Form.widget_string(name,value,_class,_id)

    @staticmethod
    def widget_date(name,value,_class='date',_id=None):
        return Form.widget_string(name,value,_class,_id)

    @staticmethod
    def widget_time(name,value,_class='time',_id=None):
        return Form.widget_string(name,value,_class,_id)

    @staticmethod
    def widget_datetime(name,value,_class='datetime',_id=None):
        return Form.widget_string(name,value,_class,_id)

    @staticmethod
    def widget_password(name,value,_class='password',_id=None):
        return Form.widget_string(name,value,_class,_id)

    @staticmethod
    def widget_boolean(name,value,_class='boolean',_id=None):
        return tag.input(_type='checkbox',_name=name,_value='t',
                         _checked='checked' if value else None,
                         _class=_class,_id=_id)

    @staticmethod
    def widget_select(name,value,options,_class='',_id=None):
        def selected(k): 'selected' if str(value)==str(k) else None
        option_items = [tag.option(n,_value=k, _selected=selected(k))
                        for k,n in options]
        return tag.select(*option_items,_name=name,_class=_class,_id=_id)

    @staticmethod
    def widget_multiple(name,values,options,_class='',_id=None):
        values = values or []
        def selected(k): 'selected' if k in values else None
        option_items = [tag.option(n,_value=k,_selected=selected(k))
                        for k,n in options]
        return tag.select(*option_items,_name=name,_class=_class,
                           _multiple='multiple',_id=name)

    def __init__(self, *fields, **attributes):
        attributes['_action'] = attributes.get('_action','')
        attributes['_method'] = attributes.get('_method','POST')
        attributes['_enctype'] = attributes.get('_enctype','multipart/form-data')
        attributes['submit'] = attributes.get('submit','Submit')
        attributes['formstyle'] = attributes.get('formstyle',Form.style_bootstrap)
        self.attributes = attributes
        self.fields = fields
        self.errors = Storage()
        self.vars = Storage()
        self.input_vars = None
        self.processed = False
        self.submitted = False
        self.accepted = False
        self.id_prefix = ''
        self.formname = 'form-'+hashlib.md5(
            ''.join(f.name for f in fields)).hexdigest()

    def process(self, keepvalues = False, csrf_methods=['POST']):

        if not self.processed:
            self.processed = True
            method = self.attributes['_method']

            # CRSF protection logic
            if method in csrf_methods:
                if self.formname in current.session:
                    token = current.session[self.formname]
                    self.formkey = self.formname + ':' + token
                else:
                    self.formkey = 'not-assigned' # but be != None

            # get appropriate input variables
            if self.attributes['_method']=='POST':
                self.input_vars = Storage(current.post_vars)
            else:
                self.input_vars = Storage(current.get_vars)

            # validate input
            if self.input_vars._formkey == self.formkey:
                self.submitted = True
                for field in self.fields:
                    value = self.input_vars.get(field.name)
                    value, error = field.validate(value)
                    if error:
                        self.errors[field.name] = error
                    else:
                        self.vars[field.name] = value
                if not self.errors:
                    self.accepted = True

            # reset formkey
            if self.formkey:
                token = str(uuid.uuid4())
                current.session[self.formname] = token
                self.formkey = self.formname+':'+token

        # reset default values in form
        if not self.submitted or (self.accepted and not keepvalues):
            for field in self.fields:
                self.input_vars[field.name] = field.default

        return self

    @staticmethod
    def style_bootstrap(form):
        fieldset = tag.fieldset()
        attr = form.attributes
        for field in form.fields:
            name = field.name
            id = form.id_prefix + name
            label = tag.label(field.label,_for=id,_class='control-label')
            value = form.input_vars.get(name)
            if field.widget:
                input = field.widget(name,value,_id=id)
            else:
                input = getattr(form,'widget_'+field.type)(name,value,_id=id)
            wrapper = tag.div(input,_class='controls')
            if name in form.errors:
                wrapper.append(tag.div(form.errors[name],_class='w3p_error'))
            if field.comment:
                wrapper.append(tag.p(field.comment,_class='help-block'))
            fieldset.append(tag.div(label,wrapper,_class='control-group'))
        submit = tag.input(_type='submit',_value=attr['submit'],
                           _class='btn btn-primary')
        fieldset.append(tag.div(submit,_class='form-actions'))
        if form.formkey:
            fieldset.append(tag.input(_name='_formkey',_type='hidden',
                                      _value=form.formkey))
        for key, value in attr.get('hidden',{}).iteritems():
            fieldset.append(tag.input(_name=key,_type='hidden',_value=value))
        attr['_class'] = attr.get('_class','form-horizontal')
        return tag.form(fieldset, **attr)

    @staticmethod
    def style_table3cols(form):
        tbody = tag.tbody()
        attr = form.attributes
        for field in form.fields:
            name = field.name
            id = form.id_prefix + name
            label = tag.label(field.label,_for=id)
            value = form.input_vars.get(name)
            if field.widget:
                input = field.widget(name,value,_id=id)
            else:
                input = getattr(form,'widget_'+field.type)(name,value,_id=id)
            wrapper = tag.td(input)
            if name in form.errors:
                wrapper.append(tag.div(form.errors[name],_class='w3p_error'))
            tbody.append(tag.tr(tag.td(label),wrapper,tag.td(field.comment)))
        submit = tag.input(_type='submit',_value=attr['submit'])
        tbody.append(tag.tr(tag.td(''),tag.td(submit),tag.td('')))
        newform = tag.form(tbody,**attr)
        if form.formkey:
            newform.append(tag.input(_name='_formkey',_type='hidden',
                                     _value=form.formkey))
        for key, value in attr.get('hidden',{}).iteritems():
            newform.append(tag.input(_name=key,_type='hidden',_value=value))
        return newform

    def as_html(self):
        return self.attributes['formstyle'](self).as_html()

class DALForm(Form):
    def __init__(self, table, record=None, record_id=None, **attributes):
        self.table = table
        self.record = record or table(record_id)
        fields = [field for field in table
                  if field.type!='id' and field.writable]
        Form.__init__(self,*fields,**attributes)
        self.id_prefix = table._tablename

    def process(self, current, keepvalues = False, csrf_token=True):
        orm.process(self, current, keepvalue = True,
                    csrf_token = csrf_token)
        if self.accepted:
            if self.record:
                self.record.update_record(**self.vars)
            else:
                self.vars.id = self.table.insert(**self.vars)
        if not self.submitted or self.processed and not keepvalues:
            for field in self.fields:
                value = self.record[field.name] if self.record \
                    else field.default
                self.input_vars[field.name] = field.formatter(value)
        return self


def test():
    from dal import Field
    form = Form(Field('name'),Field('age'))
    print form

if __name__ == '__main__':
    test()
