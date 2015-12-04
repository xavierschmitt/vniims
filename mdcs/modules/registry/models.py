from modules.builtin.models import CheckboxesModule
from modules.models import Module
from django.conf import settings
import os
from forms import NamePIDForm, DateForm
import lxml.etree as etree
from django.template import Context, Template

RESOURCES_PATH = os.path.join(settings.SITE_ROOT, 'modules', 'registry', 'resources')
TEMPLATES_PATH = os.path.join(RESOURCES_PATH, 'html')
SCRIPTS_PATH = os.path.join(RESOURCES_PATH, 'js')
STYLES_PATH = os.path.join(RESOURCES_PATH, 'css')

class RegistryCheckboxesModule(CheckboxesModule):
    
    def __init__(self, xml_tag):
                 
        self.xml_tag = xml_tag
        CheckboxesModule.__init__(self, options={}, label='', name='',
                                  styles=[os.path.join(STYLES_PATH, 'checkboxes.css')],)

    def _get_module(self, request):
        namespaces = request.session['namespaces']
        defaultPrefix = request.session['defaultPrefix']
        xmlDocTreeStr = request.session['xmlDocTree']
        xmlDocTree = etree.fromstring(xmlDocTreeStr)
    
        namespace = namespaces[defaultPrefix]
    
        xpath_namespaces = {}
        for prefix, ns in request.session['namespaces'].iteritems():
            xpath_namespaces[prefix] = ns[1:-1]
        
        # get the element where the module is attached
        xsd_element = xmlDocTree.xpath(request.GET['xsd_xpath'], namespaces=xpath_namespaces)[0]
        xsd_element_type = xsd_element.attrib['type']
        xpath_type = "./{0}simpleType[@name='{1}']".format(namespace, xsd_element_type)
        elementType = xmlDocTree.find(xpath_type)
        enumeration_list = elementType.findall('./{0}restriction/{0}enumeration'.format(namespace))
        
        for enumeration in enumeration_list:
            self.options[enumeration.attrib['value']] = enumeration.attrib['value']
        
        return CheckboxesModule.get_module(self, request)

    def _get_display(self, request):
        return ''

    def _get_result(self, request):
        return ''

    def _post_display(self, request):
        return ''

    def _post_result(self, request):
        xml_result = ''        
        if 'data[]' in request.POST:
            for value in dict(request.POST)['data[]']:
                xml_result += '<' + self.xml_tag + '>' + value + '</' + self.xml_tag + '>'
        print xml_result
        return xml_result
    
    
class NamePIDModule(Module):
    
    def __init__(self, xml_tag):
        self.xml_tag = xml_tag
        Module.__init__(self, scripts=[os.path.join(SCRIPTS_PATH, 'namepid.js')])

    def _get_module(self, request):
        with open(os.path.join(TEMPLATES_PATH, 'name_pid.html'), 'r') as template_file:
            template_content = template_file.read()    
            template = Template(template_content)
            
            self.params = {}
            if 'data' in request.GET:
                self.params['name'] = request.GET['data']
            if 'attributes' in request.GET:
                if 'pid' in request.GET['attributes']:
                    self.params['pid'] = request.GET['attributes']['pid']
            context = Context({'form': NamePIDForm(self.params)})
            return template.render(context)        


    def _get_display(self, request):
        return ''


    def _get_result(self, request):
        pid = ' pid="'+ self.params['pid'] +'"' if 'pid' in self.params else ''
        name = self.params['name'] if 'name' in self.params else ''
        return '<' + self.xml_tag + pid + '>' +  name + '</' + self.xml_tag + '>'


    def _post_display(self, request):
        form = NamePIDForm(request.POST)
        if not form.is_valid():
            return '<p style="color:red;">Entered values are not correct.</p>'
        return ''


    def _post_result(self, request):
        result_xml = ''
        
        form = NamePIDForm(request.POST)
        if form.is_valid():
            if 'name' in request.POST and request.POST['name'] != '':
                pid = ' pid="'+ request.POST['pid'] +'"' if 'pid' in request.POST else ''
                return '<' + self.xml_tag + pid + '>' +  request.POST['name'] + '</' + self.xml_tag + '>'
            
        return result_xml


  
class RelevantDateModule(Module):
    
    def __init__(self, xml_tag):
        self.xml_tag = xml_tag
        Module.__init__(self, scripts=[os.path.join(SCRIPTS_PATH, 'relevantdate.js')])


    def _get_module(self, request):
        with open(os.path.join(TEMPLATES_PATH, 'relevant_date.html'), 'r') as template_file:
            template_content = template_file.read()    
            template = Template(template_content)
            context = Context({'form': DateForm()})
            return template.render(context)        


    def _get_display(self, request):
        return ''


    def _get_result(self, request):
        return ''


    def _post_display(self, request):
        form = DateForm(request.POST)
        if not form.is_valid():
            return '<p style="color:red;">Entered values are not correct.</p>'
        return ''


    def _post_result(self, request):
        result_xml = ''
        
        form = DateForm(request.POST)
        if form.is_valid():
            if 'date' in request.POST and request.POST['date'] != '':
                role = ' role="'+ request.POST['role'] +'"' if 'role' in request.POST else ''
                return '<' + self.xml_tag + role + '>' +  request.POST['date'] + '</' + self.xml_tag + '>'
            
        return result_xml
    