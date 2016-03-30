"""
"""
import requests
from types import *

from django.http.request import HttpRequest
from django.template import loader

from os.path import join

from curate.renderer import render_li, render_buttons, render_collapse_button, \
    DefaultRenderer
from modules import get_module_view


class AbstractListRenderer(DefaultRenderer):

    def __init__(self, xsd_data):
        list_renderer_path = join('renderer', 'list')

        templates = {
            'ul': loader.get_template(join(list_renderer_path, 'ul.html'))
        }

        super(AbstractListRenderer, self).__init__(xsd_data, templates)

    def _render_ul(self, content, element_id, is_hidden=False):
        # FIXME Django SafeText type cause the test to fail
        # if type(content) not in [str, unicode]:
        #     raise TypeError('First param (content) should be a str (' + str(type(content)) + ' given)')

        if type(element_id) not in [str, unicode, NoneType]:
            raise TypeError('Second param (element_id) should be a str or None (' + str(type(element_id)) + ' given)')

        if type(is_hidden) != bool:
            raise TypeError('Third param (chosen) should be a bool (' + str(type(is_hidden)) + ' given)')

        data = {
            'content': content,
            'element_id': element_id,
            'is_hidden': is_hidden
        }

        return self._load_template('ul', data)

    def _render_li(self):
        pass


class ListRenderer(AbstractListRenderer):
    """
    """

    def __init__(self, xsd_data):
        super(ListRenderer, self).__init__(xsd_data)

    def render(self, partial=False):
        """

        Parameters:
            partial:

        :return:
        """
        html_content = ''

        if self.data.tag == 'element':
            html_content += self.render_element(self.data)
        else:
            print self.data.tag + ' not handled (render_data)'

        if not partial:
            return self._render_ul(html_content, str(self.data.pk))
        else:
            return html_content

    def render_element(self, element):
        """

        :param element:
        :return:
        """
        children = {}
        children_number = 0

        for child in element.children:
            if child.tag == 'elem-iter':
                children[child.pk] = child.children

                if len(child.children) > 0:
                    children_number += 1
            else:
                print '>> ' + child.tag + ' forwarded (rend_elem pre)'
                print '>> ' + str(child) + ' forwarded (rend_elem pre)'

        final_html = ''

        # Buttons generation (render once, reused many times)
        add_button = False
        del_button = False

        if 'max' in element.options:
            if children_number < element.options["max"] or element.options["max"] == -1:
                add_button = True

        if 'min' in element.options:
            if children_number > element.options["min"]:
                del_button = True

            # if children_number < element.options["min"]:
            #     add_button = True

        buttons = render_buttons(add_button, del_button)

        for child_key in children.keys():
            li_class = ''
            sub_elements = []
            sub_inputs = []

            for child in children[child_key]:
                if child.tag == 'complex_type':
                    sub_elements.append(self.render_complex_type(child))
                    sub_inputs.append(False)
                elif child.tag == 'simple_type':
                    sub_elements.append(self.render_simple_type(child))
                    sub_inputs.append(False)
                elif child.tag == 'input':
                    sub_elements.append(self._render_input(child.pk, child.value, '', ''))
                    sub_inputs.append(True)
                elif child.tag == 'module':
                    sub_elements.append(self.render_module(child))
                    sub_inputs.append(False)
                else:
                    print child.tag + ' not handled (rend_elem)'

            if children_number == 0:
                html_content = element.options["name"] + buttons
                li_class = 'removed'
            else:
                html_content = ''
                for child_index in xrange(len(sub_elements)):
                    if sub_inputs[child_index]:
                        html_content += element.options["name"] + sub_elements[child_index] + buttons
                    else:
                        html_content += render_collapse_button() + element.options["name"] + buttons
                        html_content += self._render_ul(sub_elements[child_index], None)

            final_html += render_li(html_content, li_class, child_key)

        return final_html

    def render_complex_type(self, element):
        """

        :param element:
        :return:
        """
        html_content = ''

        for child in element.children:
            if child.tag == 'sequence':
                html_content += self.render_sequence(child)
            elif child.tag == 'simple_content':
                html_content += self.render_simple_content(child)
            elif child.tag == 'attribute':
                html_content += self.render_attribute(child)
            elif child.tag == 'choice':
                html_content += self.render_choice(child)
            else:
                print child.tag + ' not handled (rend_ct)'

        return html_content

    def render_attribute(self, element):
        """

        :param element:
        :return:
        """
        html_content = element.options["name"]
        children = []

        for child in element.children:
            if child.tag == 'elem-iter':
                children += child.children
            else:
                print child.tag + 'not handled (rend_attr base)'

        for child in children:
            if child.tag == 'simple_type':
                html_content += self.render_simple_type(child)
            elif child.tag == 'input':
                html_content += self._render_input(child.pk, child.value, '', '')
            else:
                print child.tag + ' not handled (rend_attr)'

        return render_li(html_content, '', element.pk)

    def render_sequence(self, element):
        """

        :param element:
        :return:
        """
        html_content = ''
        children = []

        for child in element.children:
            if child.tag == 'sequence-iter':
                children += child.children
            else:
                print child.tag + '  not handled (rend_seq_pre)'

        for child in children:
            if child.tag == 'element':
                html_content += self.render_element(child)
            else:
                print child.tag + '  not handled (rend_seq)'

        return html_content

    def render_choice(self, element):
        """

        :param element:
        :return:
        """
        html_content = ''
        children = {}
        choice_values = {}

        for child in element.children:
            if child.tag == 'choice-iter':
                children[child.pk] = child.children

                choice_values[child.pk] = child.value
            else:
                print child.tag + '  not handled (rend_choice_pre)'

        sub_content = ''
        options = []

        for iter_element in children.keys():
            for child in children[iter_element]:
                element_html = ''
                is_selected_element = (str(child.pk) == choice_values[iter_element])

                if child.tag == 'element':
                    options.append((str(child.pk), child.options['name'], is_selected_element))
                    element_html = self.render_element(child)
                elif child.tag == 'sequence':
                    options.append((str(child.pk), 'sequence', is_selected_element))
                    element_html = self.render_sequence(child)
                else:
                    print child.tag + ' not handled (rend_choice)'

                if element_html != '':
                    sub_content += self._render_ul(element_html, str(child.pk), (not is_selected_element))

            html_content += 'Choice ' + self._render_select(str(iter_element), 'choice', options)
            html_content += sub_content

        return html_content

    def render_simple_content(self, element):
        """

        :param element:
        :return:
        """
        html_content = ''

        for child in element.children:
            if child.tag == 'extension':
                html_content += self.render_extension(child)
            else:
                print child.tag + '  not handled (rend_scont)'

        return html_content

    def render_simple_type(self, element):
        """

        :param element:
        :return:
        """
        html_content = ''

        for child in element.children:
            if child.tag == 'restriction':
                html_content += self.render_restriction(child)
            elif child.tag == 'attribute':
                html_content += self.render_attribute(child)
            else:
                print child.tag + '  not handled (rend_stype)'

        return html_content

    def render_extension(self, element):
        """

        :param element:
        :return:
        """
        html_content = ''

        for child in element.children:
            if child.tag == 'input':
                html_content += self._render_input(child.pk, child.value, '', '')
            elif child.tag == 'attribute':
                html_content += self.render_attribute(child)
            elif child.tag == 'simple_type':
                html_content += self.render_simple_type(child)
            else:
                print child.tag + ' not handled (rend_ext)'

        return html_content

    def render_restriction(self, element):
        """

        :param element:
        :return:
        """
        options = []
        subhtml = ''

        for child in element.children:
            if child.tag == 'enumeration':
                options.append((child.value, child.value, child.value == element.value))
            elif child.tag == 'input':
                subhtml += self._render_input(child.pk, child.value, '', '')
            else:
                print child.tag + ' not handled (rend_ext)'

        if subhtml == '' or len(options) != 0:
            return self._render_select(str(element.pk), 'restriction', options)
        else:
            return subhtml

    def render_module(self, element):
        module_options = element.options
        module_url = module_options['url']

        module_view = get_module_view(module_url)

        module_request = HttpRequest()
        module_request.method = 'GET'

        module_request.GET = {
            'module_id': element.pk,
            'url': module_url,
            'xsd_xpath': module_options['xpath']['xsd'],
            'xml_xpath': module_options['xpath']['xsd']
        }

        # if the loaded doc has data, send them to the module for initialization
        if module_options['data'] is not None:
            module_request.GET['data'] = module_options['data']

        if module_options['attributes'] is not None:
            module_request.GET['attributes'] = module_options['attributes']

        # renders the module
        return module_view(module_request).content.decode("utf-8")
