from HTMLParser import HTMLParser
from modules.builtin.models import InputModule, OptionsModule, AsyncInputModule, AutoCompleteModule
from modules.exceptions import ModuleError
from django.conf import settings
import os
from lxml import etree
from modules.xpathaccessor import XPathAccessor
from modules.models import Module


RESOURCES_PATH = os.path.join(settings.SITE_ROOT, 'modules/examples/resources/')
# SCRIPTS_PATH = os.path.join(settings.SITE_ROOT, 'modules/examples/resources/')
# STYLES_PATH = os.path.join(settings.SITE_ROOT, 'modules/examples/resources/')

class PositiveIntegerInputModule(InputModule):
    def __init__(self):
        InputModule.__init__(self, label='Enter positive integer', default_value=1)

    def _get_module(self, request):
        if 'data' in request.GET:
            self.default_value = request.GET['data']

        return InputModule.get_module(self, request)

    def _is_data_valid(self, data):
        try:
            value = int(data)
            if value >= 0:
                return True
            else:
                return False
        except ValueError:
            return False

    def _get_display(self, request):
        if 'data' in request.GET:
            self.default_value = request.GET['data']

        return str(self.default_value)+" is a valid positive integer"

    def _get_result(self, request):
        return self.default_value

    def _post_display(self, request):
        data = str(request.POST['data'])
        return data + " is a positive integer" if self._is_data_valid(data) else data + " is not a positive integer"

    def _post_result(self, request):
        data = str(request.POST['data'])
        return data if self._is_data_valid(data) else ''


class CitationRefIdModule(InputModule):
    def __init__(self):
        InputModule.__init__(self, label='TRC Ref ID', default_value='YYYY;nam;nam;n')

    def _get_module(self, request):
        if 'data' in request.GET:
            self.default_value = self._parse_data(request.GET['data'])

        return InputModule.get_module(self, request)

    def _is_data_valid(self, data):
        return True

    def _parse_data(self, data):
        if not self._is_data_valid(data):
            return None

        html = HTMLParser()
        data = html.unescape(data)

        xml_data = etree.fromstring(data)
        xml_children = []

        for xml_child in xml_data.getchildren():
            xml_children.append(xml_child.text)

        return ";".join(xml_children)

    def _get_display(self, request):
        if 'data' in request.GET:
            self.default_value = self._parse_data(request.GET['data'])

        return str(self.default_value)

    def _get_result(self, request):
        if 'data' in request.GET:
            return request.GET['data']

        return '<TRCRefID>' \
               '<yrYrPub></yrYrPub>' \
               '<sAuthor1></sAuthor1>' \
               '<sAuthor2></sAuthor2>' \
               '<nAuthorn></nAuthorn>' \
               '</TRCRefID>'

    def _post_display(self, request):
        data = str(request.POST['data'])
        return data

    def _post_result(self, request):
        data = str(request.POST['data']).split(';')

        datastr = '<TRCRefID>' \
                  '<yrYrPub>'+data[0]+'</yrYrPub>' \
                  '<sAuthor1>'+data[1]+'</sAuthor1>' \
                  '<sAuthor2>'+data[2]+'</sAuthor2>' \
                  '<nAuthorn>'+data[3]+'</nAuthorn>' \
                  '</TRCRefID>'

        return datastr


class ChemicalElementMappingModule(OptionsModule):
    
    def __init__(self):
        self.options = {
            'Ac': 'Actinium',
            'Al': 'Aluminum',
            'Ag': 'Silver',
            'Am': 'Americium',
            'Ar': 'Argon',
            'As': 'Arsenic',
            'At': 'Astatine',
            'Au': 'Gold'
        }
                
        OptionsModule.__init__(self, options=self.options, label='Select an element')

    def _get_module(self, request):
        return OptionsModule.get_module(self, request)

    def _get_display(self, request):
        return self.options.values()[0] + ' is selected'

    def _get_result(self, request):
        return self.options.keys()[0]

    def _is_data_valid(self, data):
        return data in self.options.keys()

    def _post_display(self, request):
        data = str(request.POST['data'])
        return self.options[data] + ' is selected'

    def _post_result(self, request):
        return str(request.POST['data'])


class ListToGraphInputModule(AsyncInputModule):
    
    def __init__(self):
        AsyncInputModule.__init__(self, label='Enter a list of numbers', modclass='list_to_graph',
                                  styles=[os.path.join(RESOURCES_PATH, 'css/list_to_graph.css')],
                                  scripts=["https://cdnjs.cloudflare.com/ajax/libs/d3/3.5.5/d3.min.js",
                                           os.path.join(RESOURCES_PATH, 'js/list_to_graph.js')])

    def _get_module(self, request):
        return AsyncInputModule.get_module(self, request)

    def _get_display(self, request):
        return ''

    def _get_result(self, request):
        return ''

    def _is_data_valid(self, data):
        values = data.split(' ')

        for value in values:
            try:
                int(value)
            except ValueError:
                return False

        return True

    def _post_display(self, request):
        if 'data' not in request.POST:
            raise ModuleError('No data sent to server.')

        display = "<div class='chart'></div>"

        if not self._is_data_valid(request.POST['data']):
            display = "<b style='color:red;'>Expecting a list of integer values separated by spaces.</b>"

        return display

    def _post_result(self, request):
        return request.POST['data']


class ExampleAutoCompleteModule(AutoCompleteModule):

    def __init__(self):
        self.data = [
            'Plastic',
            'Concrete',
            'Cement',
            'Material1',
            'Material2',
            'Material3',
            'Others'
        ]

        AutoCompleteModule.__init__(self, label='Material Name', scripts=[os.path.join(RESOURCES_PATH,
                                                                                       'js/example_autocomplete.js')])

    def _get_module(self, request):
        return AutoCompleteModule.get_module(self, request)

    def _get_display(self, request):
        return ''

    def _get_result(self, request):
        return ''

    def _is_data_valid(self, data):
        return True

    def _post_display(self, request):
        if 'data' not in request.POST:
            raise ModuleError('No data sent to server.')

        response_list = []

        for term in self.data:
            if request.POST['data'].lower() in term.lower():
                response_list.append(term)

        return response_list

    def _post_result(self, request):
        return ''


class SiblingsAccessorModule(OptionsModule, XPathAccessor):
    country_codes = {
                     'FRANCE': 'FR',
                     'UNITED STATES OF AMERICA': 'USA',
                     }
    
    capitals = {
                'FRANCE': 'PARIS',
                'UNITED STATES OF AMERICA': 'WASHINGTON DC',
                }
    
    anthems = {
               'FRANCE': 'La Marseillaise',
               'UNITED STATES OF AMERICA': 'The Star-Sprangled Banner',
               }
    
    flags = {
             'FRANCE': 'Tricolour',
             'UNITED STATES OF AMERICA': 'The Stars and Stripes',
             }
    
    languages = {
             'FRANCE': 'FRENCH',
             'UNITED STATES OF AMERICA': 'ENGLISH',
             }
    
    def __init__(self):
        self.options = {
            'FRANCE': 'France',
            'UNITED STATES OF AMERICA': 'USA',
        }
                
        OptionsModule.__init__(self, options=self.options, label='Select a Country')

    def _get_module(self, request):
        return OptionsModule.get_module(self, request)

    def _get_display(self, request):
        return ''

    def _get_result(self, request):        
        return self.options.keys()[0]

    def _is_data_valid(self, data):
        return data in self.options.keys()

    def _post_display(self, request):
        return ''

    def _post_result(self, request):
        # get the selected value
        value = str(request.POST['data'])
        
        # create the XPathAccessor
        XPathAccessor.__init__(self, request)
        
        return value
        
    def set_XpathAccessor(self, request):
        # get the selected value
        value = str(request.POST['data'])
        
        # get values to return for siblings
        country_code = self.country_codes[value]
        capital = self.capitals[value]
        anthem = self.anthems[value]
        language = self.languages[value]
        flag = self.flags[value]
        
         
        # get xpath of current node (for dynamic xpath building)
        module_xpath = self.get_xpath()
        parent_xpath = "/".join(module_xpath.split("/")[:-1])
        parent_xpath_idx = parent_xpath[parent_xpath.rfind("[")+1:-1]
        idx = "[" + str(parent_xpath_idx) + "]"
         
        # set nodes with values
        self.set_xpath_value('/Countries[1]/country' + idx + '/country_code[1]', country_code)
        self.set_xpath_value('/Countries[1]/country' + idx + '/details[1]/capital[1]', capital)
        self.set_xpath_value('/Countries[1]/country' + idx + '/details[1]/anthem[1]', anthem)
        self.set_xpath_value('/Countries[1]/country' + idx + '/details[1]/language[1]', language)
        self.set_xpath_value('/Countries[1]/country' + idx + '/details[1]/flag[1]', {'data': flag})


class FlagModule(Module):
    
    
    images = {
             'The Stars and Stripes': "https://upload.wikimedia.org/wikipedia/en/a/a4/Flag_of_the_United_States.svg",
             'Tricolour': "https://upload.wikimedia.org/wikipedia/commons/c/c3/Flag_of_France.svg"
             }
    
    def __init__(self):                
        Module.__init__(self)

    def _get_module(self, request):
        return ''

    def _get_display(self, request):        
        return ''

    def _get_result(self, request):
        return ''

    def _is_data_valid(self, data):
        return ''

    def _post_display(self, request):
        return "<img src='" + self.images[str(request.POST['data'])] + "' height='42' width='42'/>"

    def _post_result(self, request):
        return str(request.POST['data'])
