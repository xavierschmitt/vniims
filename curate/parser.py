"""
"""
import logging
from os.path import join

from curate.models import SchemaElement
from curate.renderer import render_buttons, render_collapse_button, \
    render_input, render_ul, \
    render_select
from mgi.models import FormElement, XMLElement, FormData, Module, Template
# from curate.renderer.list import ListRenderer
# from curate.renderer.table import TableRenderer
# from mgi.models import FormElement, XMLElement, FormData, Module, Template, MetaSchema
from mgi.settings import CURATE_MIN_TREE, CURATE_COLLAPSE
from bson.objectid import ObjectId
from mgi import common
from lxml import etree
# import django.utils.html
from io import BytesIO
from modules import get_module_view
import urllib2

# from mgi.common import LXML_SCHEMA_NAMESPACE, SCHEMA_NAMESPACE
from mgi.common import LXML_SCHEMA_NAMESPACE
from utils.XSDflattener.XSDflattener import XSDFlattenerURL

logger = logging.getLogger(__name__)


##################################################
# Part I: Utilities
##################################################

def load_schema_data_in_db(xsd_data):
    xsd_element = SchemaElement()
    xsd_element.tag = xsd_data['tag']
    xsd_element.value = xsd_data['value']

    if 'options' in xsd_data:
        xsd_element.options = xsd_data['options']

    if 'children' in xsd_data:
        children = []

        for child in xsd_data['children']:
            child_db = load_schema_data_in_db(child)
            children.append(child_db)

        if len(children) > 0:
            xsd_element.children = children

    xsd_element.save()
    return xsd_element


def get_nodes_xpath(elements, xml_tree):
    """Perform a lookup in subelements to build xpath.

    Get nodes' xpath, only one level deep. It's not going to every leaves. Only need to know if the
    node is here.

    Parameters:
        elements: XML element
        xml_tree: xml_tree
    """
    # FIXME Making one function with get_subnode_xpath should be possible, both are doing the same job
    # FIXME same problems as in get_subnodes_xpath
    xpaths = []

    for element in elements:
        if element.tag == "{0}element".format(LXML_SCHEMA_NAMESPACE):
            if 'name' in element.attrib:
                xpaths.append({'name': element.attrib['name'], 'element': element})
            elif 'ref' in element.attrib:
                ref = element.attrib['ref']
                # ref_element = None
                if ':' in ref:
                    ref_split = ref.split(":")
                    ref_name = ref_split[1]
                    ref_element = xml_tree.find("./{0}element[@name='{1}']".format(LXML_SCHEMA_NAMESPACE, ref_name))
                else:
                    ref_element = xml_tree.find("./{0}element[@name='{1}']".format(LXML_SCHEMA_NAMESPACE, ref))
                if ref_element is not None:
                    xpaths.append({'name': ref_element.attrib.get('name'), 'element': ref_element})
        else:
            xpaths.extend(get_nodes_xpath(element, xml_tree))
    return xpaths


def lookup_occurs(request, element, xml_tree, full_path, edit_data_tree):
    """Do a lookup in data to get the number of occurences of a sequence or choice without a name (not within a named
    complextype).

    get the number of times the sequence appears in the XML document that we are loading for editing
    algorithm:
    get all the possible nodes that can appear in the sequence
    for each node, count how many times it's found in the data
    the maximum count is the number of occurrences of the sequence
    only works if data are determinist enough: means we don't have an element outside the sequence, and the same in
    the sequence

    Parameters:
        request: HTTP request
        element: XML element
        xml_tree: XML schema tree
        full_path: current node XPath
        edit_data_tree: XML data tree
    """
    # FIXME this function is not returning the correct output

    # get all possible xpaths of subnodes
    xpaths = get_nodes_xpath(element, xml_tree)
    max_occurs_found = 0

    # get target namespace prefix if one declared
    xml_tree_str = etree.tostring(xml_tree)
    namespaces = common.get_namespaces(BytesIO(str(xml_tree_str)))
    target_namespace_prefix = common.get_target_namespace_prefix(namespaces, xml_tree)
    if target_namespace_prefix != '':
        target_namespace_prefix += ":"

    # check if xpaths find a match in the document
    for xpath in xpaths:
        edit_elements = edit_data_tree.xpath(full_path + '/' + target_namespace_prefix + xpath['name'], namespaces=namespaces)

        if len(edit_elements) > max_occurs_found:
            max_occurs_found = 1

            if 'maxOccurs' in xpath['element'].attrib:
                if xpath['element'].attrib != "unbounded":
                    if xpath['element'].attrib < len(edit_elements):
                        # FIXME this part of code is not reachable (hence commented)
                        # max_occurs_found = len(edit_elements)

                        exc_mess = "These data can't be loaded for now, because of the following element: "
                        exc_mess += join(full_path, xpath['name'])  # XPath of the current element

                        raise Exception(exc_mess)

    return max_occurs_found


def manage_occurences(element):
    """Store information about the occurrences of the element

    Parameters:
        element: xsd element

    Returns:
        JSON data
    """
    min_occurs = 1
    max_occurs = 1

    if 'minOccurs' in element.attrib:
        min_occurs = int(element.attrib['minOccurs'])

    if 'maxOccurs' in element.attrib:
        if element.attrib['maxOccurs'] == "unbounded":
            max_occurs = -1
        else:
            max_occurs = int(element.attrib['maxOccurs'])

    return min_occurs, max_occurs


def manage_attr_occurrences(element):
    """Store information about the occurrences of an attribute

    Parameters:
        element: XSD element

    Returns:
        JSON data
    """
    # FIXME attribute use defaults to optional not required

    min_occurs = 1
    max_occurs = 1

    if 'use' in element.attrib:
        if element.attrib['use'] == "optional":
            min_occurs = 0
        elif element.attrib['use'] == "prohibited":
            min_occurs = 0
            max_occurs = 0
        elif element.attrib['use'] == "required":
            pass

    return min_occurs, max_occurs


def has_module(element):
    """Look for a module in XML element's attributes

    Parameters:
        element: XML element

    Returns:
        True: the element has a module attribute
        False: the element doesn't have a module attribute
    """
    # FIXME remove request (unused)
    _has_module = False

    # check if a module is set for this element
    if '{http://mdcs.ns}_mod_mdcs_' in element.attrib:
        # get the url of the module
        url = element.attrib['{http://mdcs.ns}_mod_mdcs_']

        # check that the url is registered in the system
        if url in Module.objects.all().values_list('url'):
            _has_module = True

    return _has_module


def get_xml_element_data(xsd_element, xml_element):
    """Return the content of an xml element

    Parameters:
        xsd_element:
        xml_element:
    Returns:
    """
    reload_data = None
    prefix = '{0}'.format(LXML_SCHEMA_NAMESPACE)

    # get data
    if xsd_element.tag == prefix + "element":
        # leaf: get the value
        if len(list(xml_element)) == 0:
            if xml_element.text is not None:
                reload_data = xml_element.text
            else:  # if xml_element.text is None
                reload_data = ''
        else:  # branch: get the whole branch
            reload_data = etree.tostring(xml_element)
    elif xsd_element.tag == prefix + "attribute":
        pass
    elif xsd_element.tag == prefix + "complexType" or xsd_element.tag == prefix + "simpleType":
        # leaf: get the value
        if len(list(xml_element)) == 0:
            if xml_element.text is not None:
                reload_data = xml_element.text
            else:  # xml_element.text is None
                reload_data = ''
        else:  # branch: get the whole branch
            try:
                reload_data = etree.tostring(xml_element)
            except:
                # FIXME in which case would we need that?
                reload_data = str(xml_element)

    return reload_data


def get_element_type(element, xml_tree, namespaces, default_prefix, target_namespace_prefix, schema_location=None):
    """get XSD type to render. Returns the tree where the type was found.

    Parameters:
        element: XML element
        xml_tree: XSD tree of the template
        namespaces:
        default_prefix:
        target_namespace_prefix:
        schema_location

    Returns:
                    Returns the type if found
                        - complexType
                        - simpleType
                    Returns None otherwise:
                        - type from default namespace (xsd:...)
                        - no type
                    Returns:
                        - tree where the type has been found
                        - schema location where the type has been found
    """

    element_type = None
    try:
        if 'type' not in element.attrib:  # element with type declared below it
            # if tag not closed:  <element/>
            if len(list(element)) == 1:
                if element[0].tag == "{0}annotation".format(LXML_SCHEMA_NAMESPACE):
                    element_type = None
                else:
                    element_type = element[0]
            # with annotations
            elif len(list(element)) == 2:
                # FIXME Not all possibilities are tested in this case
                element_type = element[1]
            else:
                element_type = None
        else:  # element with type attribute
            if element.attrib.get('type') in common.getXSDTypes(default_prefix):
                element_type = None
            elif element.attrib.get('type') is not None:  # FIXME is it possible?
                # TODO: manage namespaces
                # test if type of the element is a simpleType
                type_name = element.attrib.get('type')
                if ':' in type_name:
                    type_ns_prefix = type_name.split(":")[0]
                    type_name = type_name.split(":")[1]
                    if type_ns_prefix != target_namespace_prefix:
                        # TODO: manage ref to imported elements (different target namespace)
                        # get all import elements
                        imports = xml_tree.findall('//{}import'.format(LXML_SCHEMA_NAMESPACE))
                        # find the referred document using the prefix
                        for el_import in imports:
                            import_ns = el_import.attrib['namespace']
                            if namespaces[type_ns_prefix] == import_ns:
                                # get the location of the schema
                                ref_xml_schema_url = el_import.attrib['schemaLocation']
                                schema_location = ref_xml_schema_url
                                # download the file
                                ref_xml_schema_file = urllib2.urlopen(ref_xml_schema_url)
                                # read the content of the file
                                ref_xml_schema_content = ref_xml_schema_file.read()
                                # build the tree
                                xml_tree = etree.parse(BytesIO(ref_xml_schema_content.encode('utf-8')))
                                # look for includes
                                includes = xml_tree.findall('//{}include'.format(LXML_SCHEMA_NAMESPACE))
                                # if includes are present
                                if len(includes) > 0:
                                    # create a flattener with the file content
                                    flattener = XSDFlattenerURL(ref_xml_schema_content)
                                    # flatten the includes
                                    ref_xml_schema_content = flattener.get_flat()
                                    # build the tree
                                    xml_tree = etree.parse(BytesIO(ref_xml_schema_content.encode('utf-8')))
                                break

                xpath = "./{0}complexType[@name='{1}']".format(LXML_SCHEMA_NAMESPACE, type_name)
                element_type = xml_tree.find(xpath)
                if element_type is None:
                    # test if type of the element is a simpleType
                    xpath = "./{0}simpleType[@name='{1}']".format(LXML_SCHEMA_NAMESPACE, type_name)
                    element_type = xml_tree.find(xpath)
    except Exception as e:
        print "Something went wrong in get_element_type: " + e.message
        element_type = None

    return element_type, xml_tree, schema_location


def remove_annotations(element):
    """Remove annotations of an element if present

    Parameters:
        element: XML element
    """
    # FIXME annotation is not always the first child

    if len(list(element)) != 0:  # If element has children
        if element[0].tag == "{0}annotation".format(LXML_SCHEMA_NAMESPACE):  # If first child is annotation
            element.remove(element[0])


##################################################
# Part II: Schema parsing
##################################################

def generate_form(request):
    """Renders HTMl form for display.

    Parameters:
        request: HTTP request

    Returns:
        rendered HTMl form
    """

    # get the xsd tree when going back and forth with review step
    if 'xmlDocTree' in request.session:
        xml_doc_data = request.session['xmlDocTree']
    else:
        template_id = request.session['currentTemplateID']
        template_object = Template.objects.get(pk=template_id)
        xml_doc_data = template_object.content

    # flatten the includes
    flattener = XSDFlattenerURL(xml_doc_data)
    xml_doc_tree_str = flattener.get_flat()
    xml_doc_tree = etree.parse(BytesIO(xml_doc_tree_str.encode('utf-8')))

    request.session['xmlDocTree'] = xml_doc_tree_str

    # init counters
    request.session['nbChoicesID'] = '0'
    request.session['nb_html_tags'] = '0'

    # init id mapping structure (html/mongo)
    if 'mapTagID' in request.session:
        del request.session['mapTagID']
    request.session['mapTagID'] = {}

    # get form data from the database (empty one or existing one)
    form_data_id = request.session['curateFormData']
    form_data = FormData.objects.get(pk=ObjectId(form_data_id))

    # if editing, get the XML data to fill the form
    edit_data_tree = None
    if request.session['curate_edit']:
        # build the tree from data
        # transform unicode to str to support XML declaration
        if form_data.xml_data is not None:
            # Load a parser able to clean the XML from blanks, comments and processing instructions
            clean_parser = etree.XMLParser(remove_blank_text=True, remove_comments=True, remove_pis=True)
            # set the parser
            etree.set_default_parser(parser=clean_parser)
            # load the XML tree from the text
            edit_data_tree = etree.XML(str(form_data.xml_data.encode('utf-8')))
        else:  # no data found, not editing
            request.session['curate_edit'] = False

    # TODO: commented extensions Registry
    # # find extensions
    # request.session['extensions'] = get_extensions(request, xml_doc_tree, namespace, default_prefix)

    # find all root elements
    elements = xml_doc_tree.findall("./{0}element".format(LXML_SCHEMA_NAMESPACE))

    try:
        # one root
        if len(elements) == 1:
            form_content = generate_element(request, elements[0], xml_doc_tree,
                                            edit_data_tree=edit_data_tree)
        # multiple roots
        elif len(elements) > 1:
            form_content = generate_choice(request, elements, xml_doc_tree, edit_data_tree=edit_data_tree)
        else:  # No root element detected
            raise Exception("No root element detected")

        root_element = load_schema_data_in_db(form_content[1])
        # request.session['form_id'] = root_element.pk

        # renderer = ListRenderer(root_element)
        # # renderer = TableRenderer(form_content[1])
        # form_string = renderer.render()

        # form_string = render_form(form_content[0])
        return root_element.pk
    except Exception as e:
        # form_string = render_form_error(e.message)
        logger.fatal("Form generation failed: " + str(e))
        return -1

    # # save the list of elements for the form
    # form_data.elements = request.session['mapTagID']
    # # save data for the current form
    # form_data.save()
    #
    # # delete temporary data structure for forms elements
    # # TODO: use mongodb ids to avoid mapping
    # del request.session['mapTagID']

    # # data are loaded, switch Edit to False, we don't need to look at the original data anymore
    # request.session['curate_edit'] = False
    #
    # return form_string


def generate_element(request, element, xml_tree, choice_info=None, full_path="",
                     edit_data_tree=None, schema_location=None):
    """Generate an HTML string that represents an XML element.

    Parameters:
        request: HTTP request
        element: XML element
        xml_tree: XML tree of the template
        choice_info:
        full_path:
        edit_data_tree:

    Returns:
        JSON data
    """
    # FIXME if elif without else need to be corrected
    # FIXME Support for unique is not present
    # FIXME Support for key / keyref
    form_string = ""
    # get appinfo elements
    app_info = common.getAppInfo(element)

    # check if the element has a module
    _has_module = has_module(element)

    # FIXME see if we can avoid these basic initialization
    # FIXME this is not necessarily true (see attributes)
    min_occurs = 1
    max_occurs = 1

    text_capitalized = ''
    element_tag = ''
    edit_elements = []
    ##############################################

    # check if XML element or attribute
    if element.tag == "{0}element".format(LXML_SCHEMA_NAMESPACE):
        min_occurs, max_occurs = manage_occurences(element)
        element_tag = 'element'
    elif element.tag == "{0}attribute".format(LXML_SCHEMA_NAMESPACE):
        min_occurs, max_occurs = manage_attr_occurrences(element)
        element_tag = 'attribute'

    # get schema namespaces
    xml_tree_str = etree.tostring(xml_tree)
    namespaces = common.get_namespaces(BytesIO(str(xml_tree_str)))

    # get the name of the element, go find the reference if there's one
    if 'ref' in element.attrib:  # type is a reference included in the document
        ref = element.attrib['ref']
        # refElement = None
        if ':' in ref:
            # split the ref element
            ref_split = ref.split(":")
            # get the namespace prefix
            ref_namespace_prefix = ref_split[0]
            # get the element name
            ref_name = ref_split[1]
            # test if referencing element within the same schema (same target namespace)
            target_namespace_prefix = common.get_target_namespace_prefix(namespaces, xml_tree)
            if target_namespace_prefix == ref_namespace_prefix:
                ref_element = xml_tree.find("./{0}{1}[@name='{2}']".format(LXML_SCHEMA_NAMESPACE,
                                                                           element_tag, ref_name))
            else:
                # TODO: manage ref to imported elements (different target namespace)
                # get all import elements
                imports = xml_tree.findall('//{}import'.format(LXML_SCHEMA_NAMESPACE))
                # find the referred document using the prefix
                for el_import in imports:
                    import_ns = el_import.attrib['namespace']
                    if namespaces[ref_namespace_prefix] == import_ns:
                        # get the location of the schema
                        ref_xml_schema_url = el_import.attrib['schemaLocation']
                        # set the schema location to save in database
                        schema_location = ref_xml_schema_url
                        # download the file
                        ref_xml_schema_file = urllib2.urlopen(ref_xml_schema_url)
                        # read the content of the file
                        ref_xml_schema_content = ref_xml_schema_file.read()
                        # build the tree
                        xml_tree = etree.parse(BytesIO(ref_xml_schema_content.encode('utf-8')))
                        # look for includes
                        includes = xml_tree.findall('//{}include'.format(LXML_SCHEMA_NAMESPACE))
                        # if includes are present
                        if len(includes) > 0:
                            # create a flattener with the file content
                            flattener = XSDFlattenerURL(ref_xml_schema_content)
                            # flatten the includes
                            ref_xml_schema_content = flattener.get_flat()
                            # build the tree
                            xml_tree = etree.parse(BytesIO(ref_xml_schema_content.encode('utf-8')))

                        ref_element = xml_tree.find("./{0}{1}[@name='{2}']".format(LXML_SCHEMA_NAMESPACE,
                                                                                   element_tag, ref_name))
                        break
        else:
            ref_element = xml_tree.find("./{0}{1}[@name='{2}']".format(LXML_SCHEMA_NAMESPACE, element_tag, ref))

        if ref_element is not None:
            text_capitalized = ref_element.attrib.get('name')
            element = ref_element
            # check if the element has a module
            _has_module = has_module(element)
        else:
            # the element was not found where it was supposed to be
            # could be a use case too complex for the current parser
            print "Ref element not found" + str(element.attrib)
            return form_string
    else:
        text_capitalized = element.attrib.get('name')

    xml_tree_str = etree.tostring(xml_tree)
    namespaces = common.get_namespaces(BytesIO(str(xml_tree_str)))
    target_namespace, target_namespace_prefix = common.get_target_namespace(namespaces, xml_tree)

    # build xpath
    # XML xpath:/root/element
    if element_tag == 'element':
        if target_namespace is not None:
            if target_namespace_prefix != '':
                if get_element_form_default(xml_tree) == "qualified":
                    full_path += '/{0}:{1}'.format(target_namespace_prefix, text_capitalized)
                elif "{0}:".format(target_namespace_prefix) in full_path:
                    full_path += '/{0}'.format(text_capitalized)
                else:
                    full_path += '/{0}:{1}'.format(target_namespace_prefix, text_capitalized)
            else:
                full_path += '/*[local-name()="{0}"]'.format(text_capitalized)
        else:
            full_path += "/{0}".format(text_capitalized)
    elif element_tag == 'attribute':
        if target_namespace is not None:
            if target_namespace_prefix != '':
                if get_attribute_form_default(xml_tree) == "qualified":
                    full_path += '/@{0}:{1}'.format(target_namespace_prefix, text_capitalized)
                elif "{0}:".format(target_namespace_prefix) in full_path:
                    full_path += '/@{0}'.format(text_capitalized)
                else:
                    full_path += '/@{0}:{1}'.format(target_namespace_prefix, text_capitalized)
            else:
                full_path += '/@*[local-name()="{0}"]'.format(text_capitalized)
        else:
            full_path += "/@{0}".format(text_capitalized)

    # print full_path

    # XSD xpath: /element/complexType/sequence
    xsd_xpath = xml_tree.getpath(element)

    # init variables for buttons management
    add_button = False
    delete_button = False
    nb_occurrences = 1  # nb of occurrences to render (can't be 0 or the user won't see this element at all)
    nb_occurrences_data = min_occurs  # nb of occurrences in loaded data or in form being rendered (can be 0)
    # xml_element = None
    use = ""
    removed = False

    # loading data in the form
    if request.session['curate_edit']:
        # get the number of occurrences in the data
        edit_elements = edit_data_tree.xpath(full_path, namespaces=namespaces)
        nb_occurrences_data = len(edit_elements)

        if nb_occurrences_data == 0:
            use = "removed"
            removed = True

        # manage buttons
        if nb_occurrences_data < max_occurs:
            add_button = True
        if nb_occurrences_data > min_occurs:
            delete_button = True

    else:  # starting an empty form
        # Don't generate the element if not necessary
        if CURATE_MIN_TREE and min_occurs == 0:
            use = "removed"
            removed = True

        if nb_occurrences_data < max_occurs:
            add_button = True
        if nb_occurrences_data > min_occurs:
            delete_button = True

    if _has_module:
        # block maxOccurs to one, the module should take care of occurrences when the element is replaced
        nb_occurrences = 1
        max_occurs = 1
    elif nb_occurrences_data > nb_occurrences:
        nb_occurrences = nb_occurrences_data

    # get the element namespace
    element_ns = get_element_namespace(element, xml_tree)
    # set the element namespace
    tag_ns = ' xmlns="{0}" '.format(element_ns) if element_ns is not None else ''
    tag_ns_prefix = ''
    if element_tag == "attribute" and target_namespace is not None:
        for prefix, ns in namespaces.iteritems():
            if ns == target_namespace:
                tag_ns_prefix = ' ns_prefix="{0}" '.format(prefix)
                break

    # get the element type
    default_prefix = common.get_default_prefix(namespaces)
    element_type, xml_tree, schema_location = get_element_type(element, xml_tree, namespaces,
                                                               default_prefix, target_namespace_prefix,
                                                               schema_location)

    xml_element = XMLElement(xsd_xpath=xsd_xpath, nbOccurs=nb_occurrences_data, minOccurs=min_occurs,
                             maxOccurs=max_occurs, schema_location=schema_location)
    xml_element.save()

    db_element = {
        'tag': element_tag,  # 'element' or 'attribute'
        'options': {
            'name': text_capitalized,
            'min': min_occurs,
            'max': max_occurs,
            'module': None if not _has_module else True,
            'xpath': {
                'xsd': xsd_xpath,
                'xml': full_path
            }
        },
        'value': None,
        'children': []
    }

    # management of elements inside a choice (don't display if not part of the currently selected choice)
    if choice_info:
        choice_id = choice_info.chooseIDStr + "-" + str(choice_info.counter)
        chosen = True

        if request.session['curate_edit']:
            if len(edit_elements) == 0:
                chosen = False

                if CURATE_MIN_TREE:
                    form_element = FormElement(html_id=choice_id, xml_element=xml_element, xml_xpath=full_path).save()

                    request.session['mapTagID'][choice_id] = str(form_element.id)

                    form_string += render_ul('', choice_id, chosen)
                    return form_string, db_element
        else:
            if choice_info.counter > 0:
                chosen = False

                if CURATE_MIN_TREE:
                    form_element = FormElement(html_id=choice_id, xml_element=xml_element, xml_xpath=full_path).save()

                    request.session['mapTagID'][choice_id] = str(form_element.id)

                    form_string += render_ul('', choice_id, chosen)
                    return form_string, db_element
    else:
        chosen = True
        choice_id = ''

    ul_content = ''

    for x in range(0, int(nb_occurrences)):
        db_elem_iter = {
            'tag': 'elem-iter',
            'value': None,
            'children': []
        }

        nb_html_tags = int(request.session['nb_html_tags'])
        tag_id = "element" + str(nb_html_tags)
        nb_html_tags += 1
        request.session['nb_html_tags'] = str(nb_html_tags)
        form_element = FormElement(html_id=tag_id, xml_element=xml_element, xml_xpath=full_path + '[' + str(x+1) + ']',
                                   name=text_capitalized).save()

        if 'mapTagID' in request.session:
            request.session['mapTagID'][tag_id] = str(form_element.id)

        # get the use from app info element
        app_info_use = app_info['use'] if 'use' in app_info else ''
        app_info_use = app_info_use if app_info_use is not None else ''
        use += ' ' + app_info_use

        # renders the name of the element
        # form_string += "<li class='" + element_tag + ' ' + use + "' id='" + str(tag_id) + "' "
        # form_string += 'tag="{0}" {1} {2}>'.format(django.utils.html.escape(text_capitalized),
        #                                            tag_ns,
        #                                            tag_ns_prefix)
        li_content = ''

        if CURATE_COLLAPSE:
            # the type is complex, can be collapsed
            if element_type is not None and element_type.tag == "{0}complexType".format(LXML_SCHEMA_NAMESPACE):
                li_content += render_collapse_button()

        label = app_info['label'] if 'label' in app_info else text_capitalized
        label = label if label is not None else ''

        li_content += label

        # add buttons to add/remove elements
        buttons = ""
        if not (add_button is False and delete_button is False):
            buttons = render_buttons(add_button, delete_button)

        # get the default value (from xsd or from loaded xml)
        default_value = ""
        if request.session['curate_edit']:
            # if elements are found at this xpath
            if len(edit_elements) > 0:
                # it is an XML element
                if element_tag == 'element':
                    # get the value of the element x
                    if edit_elements[x].text is not None:
                        # set the value of the element
                        default_value = edit_elements[x].text
                # it is an XMl attribute
                elif element_tag == 'attribute':
                    # get the value of the attribute
                    if edit_elements[x] is not None:
                        # set the value of the element
                        default_value = str(edit_elements[x])
        elif 'default' in element.attrib:
            # if the default attribute is present
            default_value = element.attrib['default']

        # if element not removed
        if not removed:
            # if module is present, replace default input by module
            if _has_module:
                form_string += generate_module(request, element, xsd_xpath, full_path, xml_tree=xml_tree,
                                               edit_data_tree=edit_data_tree)
            else:  # generate the type
                if element_type is None:  # no complex/simple type
                    placeholder = app_info['placeholder'] if 'placeholder' in app_info else ''
                    tooltip = app_info['tooltip'] if 'tooltip' in app_info else ''

                    li_content += ' '
                    li_content += render_input(default_value, placeholder, tooltip)
                    li_content += buttons

                    db_child = {
                        'tag': 'input',
                        'value': default_value
                    }
                    db_elem_iter['children'].append(db_child)
                else:  # complex/simple type
                    li_content += buttons

                    if element_type.tag == "{0}complexType".format(LXML_SCHEMA_NAMESPACE):
                        complex_type_result = generate_complex_type(request, element_type, xml_tree,
                                                             full_path=full_path+'[' + str(x+1) + ']',
                                                             edit_data_tree=edit_data_tree,
                                                             schema_location=schema_location)

                        li_content += complex_type_result[0]
                        db_elem_iter['children'].append(complex_type_result[1])
                    elif element_type.tag == "{0}simpleType".format(LXML_SCHEMA_NAMESPACE):
                        simple_type_result = generate_simple_type(request, element_type, xml_tree,
                                                            full_path=full_path+'[' + str(x+1) + ']',
                                                            edit_data_tree=edit_data_tree, default_value=default_value,
                                                            schema_location=schema_location)

                        li_content += simple_type_result[0]
                        db_elem_iter['children'].append(simple_type_result[1])
        else:
            li_content += buttons

        # renders the name of the element
        # ul_content += render_li(li_content, tag_id, element_tag, use, text_capitalized)

        # if len(db_elem_iter['children']) > 0:
        db_element['children'].append(db_elem_iter)

    form_string += render_ul(ul_content, choice_id, chosen)
    return form_string, db_element


def get_element_form_default(xsd_tree):

    # default value
    element_form_default = "unqualified"

    root = xsd_tree.getroot()
    if 'elementFormDefault' in root.attrib:
        element_form_default = root.attrib['elementFormDefault']

    return element_form_default


def get_attribute_form_default(xsd_tree):

    # default value
    attribute_form_default = "unqualified"

    root = xsd_tree.getroot()
    if 'attributeFormDefault' in root.attrib:
        attribute_form_default = root.attrib['attributeFormDefault']

    return attribute_form_default


def get_element_namespace(element, xsd_tree):
    """
    get_element_tag
    :param element:
    :param xsd_tree:
    :param is_root:
    :return:
    """
    # get the root of the XSD document
    xsd_root = xsd_tree.getroot()

    # None by default, None means no namespace information needed, different from empty namespace
    element_ns = None

    # check if the element is root
    is_root = False
    # get XSD xpath
    xsd_path = xsd_tree.getpath(element)
    # the element is global (/xs:schema/xs:element)
    if xsd_path.count('/') == 2:
        is_root = True

    # root is always qualified, root from other schemas too
    if is_root:
        # if in a targetNamespace
        if 'targetNamespace' in xsd_root.attrib:
            # get the target namespace
            target_namespace = xsd_root.attrib['targetNamespace']
            element_ns = target_namespace
    else:
        # qualified elements
        if 'elementFormDefault' in xsd_root.attrib and xsd_root.attrib['elementFormDefault'] == 'qualified'\
                or 'attributeFormDefault' in xsd_root.attrib and xsd_root.attrib['attributeFormDefault'] == 'qualified':
            if 'targetNamespace' in xsd_root.attrib:
                # get the target namespace
                target_namespace = xsd_root.attrib['targetNamespace']
                element_ns = target_namespace
        # unqualified elements
        else:
            if 'targetNamespace' in xsd_root.attrib:
                element_ns = ""

    # print tag_ns
    return element_ns


def generate_element_absent(request, element, xml_doc_tree, form_element, schema_location=None):
    """
    # Inputs:        request -
    # Outputs:       JSON data
    # Exceptions:    None
    # Description:   Generate XML element for which the element is absent from the form
    Parameters:
        request:
        element:
        xml_doc_tree:
        form_element:

    Returns:
    """
    # TODO see if it is possibe to group with generate_element
    form_string = ""

    db_element = {
        'tag': 'elem-iter',
        'value': None,
        'children': []
    }

    # get appinfo elements
    app_info = common.getAppInfo(element)

    # check if the element has a module
    _has_module = has_module(element)

    # type is a reference included in the document
    if 'ref' in element.attrib:
        ref = element.attrib['ref']
        # refElement = None

        if ':' in ref:
            ref_split = ref.split(":")
            ref_name = ref_split[1]
            ref_element = xml_doc_tree.find("./{0}element[@name='{1}']".format(LXML_SCHEMA_NAMESPACE, ref_name))
        else:
            ref_element = xml_doc_tree.find("./{0}element[@name='{1}']".format(LXML_SCHEMA_NAMESPACE, ref))

        if ref_element is not None:
            element = ref_element
            # check if the element has a module
            _has_module = has_module(element)

    if _has_module:
        form_string += generate_module(request, element, form_element.xml_element.xsd_xpath,
                                       form_element.xml_xpath)

        db_element['module'] = True
    else:
        xml_tree_str = etree.tostring(xml_doc_tree)
        namespaces = common.get_namespaces(BytesIO(str(xml_tree_str)))
        default_prefix = common.get_default_prefix(namespaces)
        target_namespace_prefix = common.get_target_namespace_prefix(namespaces, xml_doc_tree)
        element_type, xml_doc_tree, schema_location = get_element_type(element, xml_doc_tree, namespaces,
                                                                       default_prefix, target_namespace_prefix,
                                                                       schema_location)

        # render the type
        if element_type is None:  # no complex/simple type
            default_value = ""

            if 'default' in element.attrib:
                # if the default attribute is present
                default_value = element.attrib['default']

            placeholder = app_info['placeholder'] if 'placeholder' in app_info else ''
            tooltip = app_info['tooltip'] if 'tooltip' in app_info else ''

            form_string += render_input(default_value, placeholder, tooltip)

            db_child = {
                'tag': 'input',
                'value': ''
            }

            db_element['children'].append(db_child)
        else:  # complex/simple type
            if element_type.tag == "{0}complexType".format(LXML_SCHEMA_NAMESPACE):
                complex_type_result = generate_complex_type(request, element_type, xml_doc_tree,
                                                     full_path=form_element.options['xpath']['xml'], schema_location=schema_location)

                form_string += complex_type_result[0]
                db_element['children'].append(complex_type_result[1])
            elif element_type.tag == "{0}simpleType".format(LXML_SCHEMA_NAMESPACE):
                simple_type_result = generate_simple_type(request, element_type, xml_doc_tree,
                                                    full_path=form_element.options['xpath']['xml'], schema_location=schema_location)

                form_string += simple_type_result[0]
                db_element['children'].append(simple_type_result[1])

    # return form_string, db_element
    return form_string, db_element


def generate_sequence(request, element, xml_tree, choice_info=None, full_path="", edit_data_tree=None, schema_location=None):
    """Generates a section of the form that represents an XML sequence

    Parameters:
        request:
        element: XML element
        xml_tree: XML Tree
        choice_info:
        full_path:
        edit_data_tree:

    Returns:       HTML string representing a sequence
    """
    # (annotation?,(element|group|choice|sequence|any)*)
    # FIXME implement group, any
    form_string = ""

    # remove the annotations
    remove_annotations(element)

    min_occurs, max_occurs = manage_occurences(element)

    # XSD xpath
    xsd_xpath = xml_tree.getpath(element)

    db_element = {
        'tag': 'sequence',
        'options': {
            'min': min_occurs,
            'max': max_occurs,
            'xpath': {
                'xsd': xsd_xpath,
                'xml': full_path
            }
        },
        'value': None,
        'children': []
    }

    if min_occurs != 1 or max_occurs != 1:
        text = "Sequence"

        # init variables for buttons management
        add_button = False
        delete_button = False
        nb_occurrences = 1  # nb of occurrences to render (can't be 0 or the user won't see this element at all)
        nb_occurrences_data = min_occurs  # nb of occurrences in loaded data or in form being rendered (can be 0)
        # xml_element = None

        # loading data in the form
        if request.session['curate_edit']:
            # get the number of occurrences in the data
            nb_occurrences_data = lookup_occurs(request, element, xml_tree, full_path, edit_data_tree)

            # manage buttons
            if nb_occurrences_data < max_occurs:
                add_button = True
            if nb_occurrences_data > min_occurs:
                delete_button = True
        else:  # starting an empty form
            # Don't generate the element if not necessary
            if CURATE_MIN_TREE and min_occurs == 0:
                add_button = True
                delete_button = False
            else:
                if nb_occurrences_data < max_occurs:
                    add_button = True
                if nb_occurrences_data > min_occurs:
                    delete_button = True

        if nb_occurrences_data > nb_occurrences:
            nb_occurrences = nb_occurrences_data

        xml_element = XMLElement(xsd_xpath=xsd_xpath, nbOccurs=nb_occurrences_data, minOccurs=min_occurs,
                                 maxOccurs=max_occurs, schema_location=schema_location).save()

        # keeps track of elements to display depending on the selected choice
        if choice_info:
            chosen = True
            choice_id = choice_info.chooseIDStr + "-" + str(choice_info.counter)

            if request.session['curate_edit']:
                if nb_occurrences == 0:
                    chosen = False

                    if CURATE_MIN_TREE:
                        form_element = FormElement(html_id=choice_id, xml_element=xml_element, xml_xpath=full_path).save()
                        request.session['mapTagID'][choice_id] = str(form_element.id)

                        form_string += render_ul('', choice_id, chosen)
                        return form_string, db_element
            else:
                if choice_info.counter > 0:
                    chosen = False

                    if CURATE_MIN_TREE:
                        form_element = FormElement(html_id=choice_id, xml_element=xml_element, xml_xpath=full_path).save()
                        request.session['mapTagID'][choice_id] = str(form_element.id)

                        form_string += render_ul('', choice_id, chosen)
                        return form_string, db_element
        else:
            chosen = True
            choice_id = ''

        ul_content = ''

        # editing data and sequence not found in data
        # if nb_occurrences_data == 0:
        #     nb_html_tags = int(request.session['nb_html_tags'])
        #     tag_id = "element" + str(nb_html_tags)
        #     nb_html_tags += 1
        #     request.session['nb_html_tags'] = str(nb_html_tags)
        #     form_element = FormElement(html_id=tag_id, xml_element=xml_element, xml_xpath=full_path + '[1]').save()
        #     request.session['mapTagID'][tag_id] = str(form_element.id)
        #
        #     li_content = ''
        #
        #     if CURATE_COLLAPSE:
        #         li_content += render_collapse_button()
        #
        #     li_content += text
        #     li_content += render_buttons(True, False, str(tag_id[7:]))
        #
        #     # ul_content += render_li(li_content, tag_id, 'sequence', 'removed')
        # else:
        for x in range(0, int(nb_occurrences)):
            db_elem_iter = {
                'tag': 'sequence-iter',
                'value': None,
                'children': []
            }

            nb_html_tags = int(request.session['nb_html_tags'])
            tag_id = "element" + str(nb_html_tags)
            nb_html_tags += 1
            request.session['nb_html_tags'] = str(nb_html_tags)
#                 if (minOccurs != 1) or (maxOccurs != 1):
            form_element = FormElement(html_id=tag_id, xml_element=xml_element,
                                       xml_xpath=full_path + '[' + str(x+1) + ']')
            form_element.save()
            request.session['mapTagID'][tag_id] = str(form_element.pk)

            li_content = ''

            if len(list(element)) > 0 and CURATE_COLLAPSE:
                li_content += render_collapse_button()

            li_content += text
            li_content += render_buttons(add_button, delete_button, str(tag_id[7:]))

            # generates the sequence
            for child in element:
                if child.tag == "{0}element".format(LXML_SCHEMA_NAMESPACE):
                    element_result = generate_element(request, child, xml_tree, choice_info,
                                                    full_path=full_path, edit_data_tree=edit_data_tree,
                                                    schema_location=schema_location)

                    li_content += element_result[0]
                    db_elem_iter['children'].append(element_result[1])
                elif child.tag == "{0}sequence".format(LXML_SCHEMA_NAMESPACE):
                    sequence_result = generate_sequence(request, child, xml_tree, choice_info,
                                                     full_path=full_path, edit_data_tree=edit_data_tree,
                                                     schema_location=schema_location)

                    li_content += sequence_result[0]
                    db_elem_iter['children'].append(sequence_result[1])
                elif child.tag == "{0}choice".format(LXML_SCHEMA_NAMESPACE):
                    choice_result = generate_choice(request, child, xml_tree, choice_info,
                                                   full_path=full_path, edit_data_tree=edit_data_tree,
                                                   schema_location=schema_location)

                    li_content += choice_result[0]
                    db_elem_iter['children'].append(choice_result[1])
                elif child.tag == "{0}any".format(LXML_SCHEMA_NAMESPACE):
                    pass
                elif child.tag == "{0}group".format(LXML_SCHEMA_NAMESPACE):
                    pass

            db_element['children'].append(db_elem_iter)
            # ul_content += render_li(li_content, tag_id, 'sequence')

        form_string += render_ul(ul_content, choice_id, chosen)
    else:  # min_occurs == 1 and max_occurs == 1
        db_elem_iter = {
            'tag': 'sequence-iter',
            'value': None,
            'children': []
        }

        # XSD xpath
        xsd_xpath = xml_tree.getpath(element)

        # init variables for buttons management
        nb_occurrences = 1  # nb of occurrences to render (can't be 0 or the user won't see this element at all)
        nb_occurrences_data = min_occurs  # nb of occurrences in loaded data or in form being rendered (can be 0)

        xml_element = XMLElement(xsd_xpath=xsd_xpath, nbOccurs=nb_occurrences_data, minOccurs=min_occurs,
                                 maxOccurs=max_occurs, schema_location=schema_location).save()

        if choice_info:
            choice_id = choice_info.chooseIDStr + "-" + str(choice_info.counter)
            if request.session['curate_edit']:
                if nb_occurrences == 0:
                    form_string += "<ul id=\"" + choice_id + "\" class=\"notchosen\">"
                    if CURATE_MIN_TREE:
                        form_element = FormElement(html_id=choice_id, xml_element=xml_element, xml_xpath=full_path).save()
                        request.session['mapTagID'][choice_id] = str(form_element.id)
                        form_string += "</ul>"
                        return form_string
                else:
                    form_string += "<ul id=\"" + choice_id + "\" >"
            else:
                if choice_info.counter > 0:
                    form_string += "<ul id=\"" + choice_id + "\" class=\"notchosen\">"
                    if CURATE_MIN_TREE:
                        form_element = FormElement(html_id=choice_id, xml_element=xml_element, xml_xpath=full_path).save()
                        request.session['mapTagID'][choice_id] = str(form_element.id)
                        form_string += "</ul>"
                        return form_string
                else:
                    form_string += "<ul id=\"" + choice_id + "\" >"

        # generates the sequence
        for child in element:
            if child.tag == "{0}element".format(LXML_SCHEMA_NAMESPACE):
                element_result = generate_element(request, child, xml_tree, choice_info,
                                                full_path=full_path, edit_data_tree=edit_data_tree,
                                                schema_location=schema_location)

                form_string += element_result[0]
                db_element['children'].append(element_result[1])
            elif child.tag == "{0}sequence".format(LXML_SCHEMA_NAMESPACE):
                sequence_result = generate_sequence(request, child, xml_tree, choice_info,
                                                 full_path=full_path, edit_data_tree=edit_data_tree,
                                                 schema_location=schema_location)

                form_string += sequence_result[0]
                db_element['children'].append(sequence_result[1])
            elif child.tag == "{0}choice".format(LXML_SCHEMA_NAMESPACE):
                choice_result = generate_choice(request, child, xml_tree, choice_info,
                                               full_path=full_path, edit_data_tree=edit_data_tree,
                                               schema_location=schema_location)

                form_string += choice_result[0]
                db_element['children'].append(choice_result[1])
            elif child.tag == "{0}any".format(LXML_SCHEMA_NAMESPACE):
                pass
            elif child.tag == "{0}group".format(LXML_SCHEMA_NAMESPACE):
                pass

        db_element['children'].append(db_elem_iter)

        # close the list
        if choice_info:
            form_string += "</ul>"

    return form_string, db_element


def generate_sequence_absent(request, element, xml_tree, schema_location=None):
    """Generates a section of the form that represents an XML sequence

    Parameters:
        request:
        element: XML element
        xml_tree: XML Tree
    Returns:
        HTML string representing a sequence
    """
    # TODO see if it can be merged in generate_sequence
    form_string = ""
    db_element = {
        'tag': 'sequence-iter',
        'value': None,
        'children': []
    }

    # generates the sequence
    for child in element:
        if child.tag == "{0}element".format(LXML_SCHEMA_NAMESPACE):
            element = generate_element(request, child, xml_tree, schema_location=schema_location)

            form_string += element[0]
            db_element['children'].append(element[1])
        elif child.tag == "{0}sequence".format(LXML_SCHEMA_NAMESPACE):
            sequence = generate_sequence(request, child, xml_tree, schema_location=schema_location)

            form_string += sequence[0]
            db_element['children'].append(sequence[1])
        elif child.tag == "{0}choice".format(LXML_SCHEMA_NAMESPACE):
            choice = generate_choice(request, child, xml_tree, schema_location=schema_location)

            form_string += choice[0]
            db_element['children'].append(choice[1])
        elif child.tag == "{0}any".format(LXML_SCHEMA_NAMESPACE):
            pass
        elif child.tag == "{0}group".format(LXML_SCHEMA_NAMESPACE):
            pass

    # return form_string, db_element
    return form_string, db_element


def generate_choice(request, element, xml_tree, choice_info=None, full_path="", edit_data_tree=None, schema_location=None):
    """Generates a section of the form that represents an XML choice

    Parameters:
        request:
        element: XML element
        xml_tree: XML Tree
        choice_info: to keep track of branches to display (chosen ones) when going recursively down the tree
        full_path: XML xpath being built
        edit_data_tree: XML tree of data being edited

    Returns:       HTML string representing a sequence
    """
    # (annotation?, (element|group|choice|sequence|any)*)
    # FIXME Group not supported
    # FIXME Choice not supported
    form_string = ""
    db_element = {
        'tag': 'choice',
        'xpath': {
            'xsd': None,
            'xml': full_path
        },
        'value': None,
        'children': []
    }

    # remove the annotations
    remove_annotations(element)

    # init variables for buttons management
    add_button = False
    delete_button = False
    nb_occurrences = 1  # nb of occurrences to render (can't be 0 or the user won't see this element at all)
    # nb_occurrences_data = 1
    xml_element = None

    # not multiple roots
    # FIXME process differently this part
    if not isinstance(element, list):
        # XSD xpath: don't need it when multiple root (can't duplicate a root)
        xsd_xpath = xml_tree.getpath(element)

        db_element['xpath']['xsd'] = xsd_xpath

        # get element's min/max occurs attributes
        min_occurs, max_occurs = manage_occurences(element)
        nb_occurrences_data = min_occurs  # nb of occurrences in loaded data or in form being rendered (can be 0)

        # loading data in the form
        if request.session['curate_edit']:
            # get the number of occurrences in the data
            nb_occurrences_data = lookup_occurs(request, element, xml_tree, full_path, edit_data_tree)

            if nb_occurrences_data < max_occurs:
                add_button = True
            if nb_occurrences_data > min_occurs:
                delete_button = True
        else:  # starting an empty form
            # Don't generate the element if not necessary
            if CURATE_MIN_TREE and min_occurs == 0:
                add_button = True
                delete_button = False
            else:
                if nb_occurrences_data < max_occurs:
                    add_button = True
                if nb_occurrences_data > min_occurs:
                    delete_button = True

        if nb_occurrences_data > nb_occurrences:
            nb_occurrences = nb_occurrences_data

        xml_element = XMLElement(xsd_xpath=xsd_xpath, nbOccurs=nb_occurrences_data, minOccurs=min_occurs,
                                 maxOccurs=max_occurs,schema_location=schema_location)
        xml_element.save()

        # 'occurs' key contains the tuple (minOccurs, nbOccurs, maxOccurs)
        # db_element['options'] = (min_occurs, nb_occurrences_data, max_occurs)
        db_element['options'] = {
            'min': min_occurs,
            'max': max_occurs
        }

    # keeps track of elements to display depending on the selected choice
    if choice_info:
        choice_id = choice_info.chooseIDStr + "-" + str(choice_info.counter)
        chosen = True

        if request.session['curate_edit']:
            if nb_occurrences == 0:
                chosen = False

                if CURATE_MIN_TREE:
                    form_element = FormElement(html_id=choice_id, xml_element=xml_element, xml_xpath=full_path).save()
                    request.session['mapTagID'][choice_id] = str(form_element.id)

                    form_string += render_ul('', choice_id, chosen)
                    return form_string, db_element
        else:
            if choice_info.counter > 0:
                chosen = False

                if CURATE_MIN_TREE:
                    form_element = FormElement(html_id=choice_id, xml_element=xml_element, xml_xpath=full_path).save()
                    request.session['mapTagID'][choice_id] = str(form_element.id)

                    form_string += render_ul('', choice_id, chosen)
                    return form_string, db_element
    else:
        choice_id = ''
        chosen = True

    ul_content = ''

    for x in range(0, int(nb_occurrences)):
        db_child = {
            'tag': 'choice-iter',
            'value': None,
            'children': []
        }

        nb_html_tags = int(request.session['nb_html_tags'])
        tag_id = "element" + str(nb_html_tags)
        nb_html_tags += 1
        request.session['nb_html_tags'] = str(nb_html_tags)

        form_element = FormElement(html_id=tag_id, xml_element=xml_element,
                                   xml_xpath=full_path + '[' + str(x+1) + ']')
        form_element.save()

        request.session['mapTagID'][tag_id] = str(form_element.pk)

        nb_choices_id = int(request.session['nbChoicesID'])
        choose_id = nb_choices_id
        choose_id_str = 'choice' + str(choose_id)
        nb_choices_id += 1

        request.session['nbChoicesID'] = str(nb_choices_id)

        is_removed = (nb_occurrences == 0)
        li_content = ''
        nb_sequence = 1
        options = []

        # FIXME list of children is read twice (could be parsed in one pass)
        # generates the choice
        # if len(list(element)) != 0:
        for child in element:
            entry = None

            if child.tag == "{0}element".format(LXML_SCHEMA_NAMESPACE):
                if child.attrib.get('name') is not None:
                    opt_value = opt_label = child.attrib.get('name')
                else:
                    opt_value = opt_label = child.attrib.get('ref')

                    if ':' in child.attrib.get('ref'):
                        opt_label = opt_label.split(':')[1]

                # look for active choice when editing
                element_path = full_path + '/' + opt_label
                entry = (opt_label, opt_value)

                if request.session['curate_edit']:
                    # get the schema namespaces
                    xml_tree_str = etree.tostring(xml_tree)
                    namespaces = common.get_namespaces(BytesIO(str(xml_tree_str)))
                    if len(edit_data_tree.xpath(element_path, namespaces=namespaces)) == 0:
                        entry += (True,)
                    else:
                        entry += (False,)
                else:
                    entry += (False,)

            elif child.tag == "{0}group".format(LXML_SCHEMA_NAMESPACE):
                pass
            elif child.tag == "{0}choice".format(LXML_SCHEMA_NAMESPACE):
                pass
            elif child.tag == "{0}sequence".format(LXML_SCHEMA_NAMESPACE):
                entry = ('sequence' + str(nb_sequence), 'Sequence ' + str(nb_sequence), False)
                nb_sequence += 1
            elif child.tag == "{0}any".format(LXML_SCHEMA_NAMESPACE):
                pass

        if entry is not None:
            options.append(entry)

        li_content += render_select(choose_id_str, options)
        li_content += render_buttons(add_button, delete_button, tag_id[7:])

        for (counter, choiceChild) in enumerate(list(element)):
            if choiceChild.tag == "{0}element".format(LXML_SCHEMA_NAMESPACE):
                element_result = generate_element(request, choiceChild, xml_tree,
                                                common.ChoiceInfo(choose_id_str, counter), full_path=full_path,
                                                edit_data_tree=edit_data_tree, schema_location=schema_location)

                li_content += element_result[0]
                db_child_0 = element_result[1]
                db_child['children'].append(db_child_0)
            elif choiceChild.tag == "{0}group".format(LXML_SCHEMA_NAMESPACE):
                pass
            elif choiceChild.tag == "{0}choice".format(LXML_SCHEMA_NAMESPACE):
                pass
            elif choiceChild.tag == "{0}sequence".format(LXML_SCHEMA_NAMESPACE):
                sequence = generate_sequence(request, choiceChild, xml_tree,
                                                 common.ChoiceInfo(choose_id_str, counter), full_path=full_path,
                                                 edit_data_tree=edit_data_tree, schema_location=schema_location)

                li_content += sequence[0]
                db_child_0 = sequence[1]
                db_child['children'].append(db_child_0)
            elif choiceChild.tag == "{0}any".format(LXML_SCHEMA_NAMESPACE):
                pass

        # ul_content += render_li('Choose'+li_content, tag_id, 'choice', 'removed' if is_removed else None)
        db_element['children'].append(db_child)

    form_string += render_ul(ul_content, choice_id, chosen)
    return form_string, db_element


def generate_simple_type(request, element, xml_tree, full_path, edit_data_tree=None,
                         default_value=None, schema_location=None):
    """Generates a section of the form that represents an XML simple type

    Parameters:
        request:
        element:
        xml_tree:
        full_path:
        edit_data_tree:
        default_value:

    Returns:
        HTML string representing a simple type
    """
    # FIXME implement union, correct list
    form_string = ""
    db_element = {
        'tag': 'simple_type',
        'value': None,
        'children': []
    }

    # remove the annotations
    remove_annotations(element)

    if has_module(element):
        # XSD xpath: /element/complexType/sequence
        xsd_xpath = xml_tree.getpath(element)
        form_string += generate_module(request, element, xsd_xpath, full_path, xml_tree=xml_tree,
                                       edit_data_tree=edit_data_tree)
        db_element['module'] = True

        return form_string, db_element

    if list(element) != 0:
        child = element[0]

        if child.tag == "{0}restriction".format(LXML_SCHEMA_NAMESPACE):
            restriction = generate_restriction(request, child, xml_tree, full_path, edit_data_tree=edit_data_tree,
                                                default_value=default_value, schema_location=schema_location)

            form_string += restriction[0]
            db_child = restriction[1]
        elif child.tag == "{0}list".format(LXML_SCHEMA_NAMESPACE):
            # TODO list can contain a restriction/enumeration
            form_string += render_input(default_value, '', '')

            db_child = {
                'tag': 'list',
                'value': '',
                'children': []
            }
        elif child.tag == "{0}union".format(LXML_SCHEMA_NAMESPACE):
            # TODO: provide UI for unions
            form_string += render_input(default_value, '', '')

            db_child = {
                'tag': 'union',
                'value': None,
                'children': []
            }
        else:
            db_child = {
                'tag': 'error'
            }

        db_element['children'].append(db_child)

    return form_string, db_element
    # return form_string


def generate_complex_type(request, element, xml_tree, full_path, edit_data_tree=None, schema_location=None):
    """Generates a section of the form that represents an XML complexType

    Parameters:
        request:
        element: XML element
        xml_tree: XML Tree
        full_path:
        edit_data_tree:

    Returns:
        HTML string representing a sequence
    """
    # FIXME add support for complexContent, group, attributeGroup, anyAttribute
    # (
    #   annotation?,
    #   (
    #       simpleContent|complexContent|(
    #           (group|all|choice|sequence)?,
    #           (
    #               (attribute|attributeGroup)*,
    #               anyAttribute?
    #           )
    #       )
    #   )
    # )

    form_string = ""
    db_element = {
        'tag': 'complex_type',
        'value': None,
        'children': []
    }

    # remove the annotations
    remove_annotations(element)

    if has_module(element):
        # XSD xpath: /element/complexType/sequence
        xsd_xpath = xml_tree.getpath(element)
        form_string += generate_module(request, element, xsd_xpath, full_path, xml_tree=xml_tree,
                                       edit_data_tree=edit_data_tree)

        db_element['options'] = {
            'mod': True
        }

        return form_string, db_element

    # is it a simple content?
    complexTypeChild = element.find('{0}simpleContent'.format(LXML_SCHEMA_NAMESPACE))
    if complexTypeChild is not None:
        result_simple_content = generate_simple_content(request, complexTypeChild, xml_tree, full_path=full_path,
                                              edit_data_tree=edit_data_tree, schema_location=schema_location)

        form_string += result_simple_content[0]
        db_element['children'].append(result_simple_content[1])

        return form_string, db_element

    # is it a complex content?
    complexTypeChild = element.find('{0}complexContent'.format(LXML_SCHEMA_NAMESPACE))
    if complexTypeChild is not None:
        complex_content_result = generate_complex_content(request, complexTypeChild, xml_tree, full_path=full_path,
                                               edit_data_tree=edit_data_tree, schema_location=schema_location)
        form_string += complex_content_result[0]
        db_element['children'].append(complex_content_result[1])

        return form_string, db_element

    # does it contain any attributes?
    complexTypeChildren = element.findall('{0}attribute'.format(LXML_SCHEMA_NAMESPACE))
    if len(complexTypeChildren) > 0:
        for attribute in complexTypeChildren:
            element_result = generate_element(request, attribute, xml_tree, full_path=full_path,
                                           edit_data_tree=edit_data_tree, schema_location=schema_location)

            form_string += element_result[0]
            db_element['children'].append(element_result[1])
    # does it contain sequence or all?
    complexTypeChild = element.find('{0}sequence'.format(LXML_SCHEMA_NAMESPACE))
    if complexTypeChild is not None:
        sequence_result = generate_sequence(request, complexTypeChild, xml_tree, full_path=full_path,
                                        edit_data_tree=edit_data_tree, schema_location=schema_location)

        form_string += sequence_result[0]
        db_element['children'].append(sequence_result[1])
    else:
        complexTypeChild = element.find('{0}all'.format(LXML_SCHEMA_NAMESPACE))
        if complexTypeChild is not None:
            sequence_result = generate_sequence(request, complexTypeChild, xml_tree, full_path=full_path,
                                            edit_data_tree=edit_data_tree, schema_location=schema_location)

            form_string += sequence_result[0]
            db_element['children'].append(sequence_result[1])
        else:
            # does it contain choice ?
            complexTypeChild = element.find('{0}choice'.format(LXML_SCHEMA_NAMESPACE))
            if complexTypeChild is not None:
                choice_result = generate_choice(request, complexTypeChild, xml_tree, full_path=full_path,
                                              edit_data_tree=edit_data_tree, schema_location=schema_location)

                form_string += choice_result[0]
                db_element['children'].append(choice_result[1])

    # TODO: commented extensions Registry
    # # check if the type has a name (for reference)
    # if 'name' in element.attrib:
    #     # check if types extend this one
    #     extensions = request.session['extensions']
    #
    #     # the complextype has some possible extensions
    #     if element.attrib['name'] in extensions.keys():
    #         # get all extensions associated with the type
    #         current_type_extensions = extensions[element.attrib['name']]
    #
    #         # build namesapces to use with xpath
    #         xpath_namespaces = {}
    #         for prefix, ns in request.session['namespaces'].iteritems() :
    #             xpath_namespaces[prefix] = ns[1:-1]
    #
    #         # get extension types using XPath
    #         extension_types = []
    #         for current_type_extension in current_type_extensions:
    #             # get the extension using its xpath
    #             extension_element = xml_tree.xpath(current_type_extension, namespaces=xpath_namespaces)[0]
    #             extension_types.append(extension_element)
    #
    #
    #         formString += '<div class="extension">'
    #         formString += 'Extend <select onchange="changeExtension()">'
    #         formString += '<option> --------- </option>'
    #
    #         # browse extension types
    #         for extension_type in extension_types:
    #             formString += '<option>'
    #             # get the closest type name: parent -> xxxContent, parent -> xxxType
    #             formString += extension_type.getparent().getparent().attrib['name']
    #             formString += '</option>'
    #
    #         formString += '</select>'
    #         formString += '</div>'
    #         # if extension_element.tag == "{0}complexType".format(namespace):
    #         #     pass
    #         # elif extension_element.tag == "{0}simpleType".format(namespace):
    #         #     pass
    return form_string, db_element


def generate_complex_content(request, element, xml_tree, full_path, edit_data_tree=None, schema_location=None):
    """
    Inputs:        request -
                   element - XML element
                   xmlTree - XML Tree
    Outputs:       HTML string representing a sequence
    Exceptions:    None
    Description:   Generates a section of the form that represents an XML complex content
    :param request:
    :param element:
    :param xmlTree:
    :param fullPath:
    :param edit_data_tree:
    :return:
    """
    #(annotation?,(restriction|extension))

    form_string = ""
    db_element = {
        'tag': 'complex_content',
        'value': None,
        'children': []
    }

    # remove the annotations
    remove_annotations(element)

    # generates the content
    if len(list(element)) != 0:
        child = element[0]
        if child.tag == "{0}restriction".format(LXML_SCHEMA_NAMESPACE):
            restriction_result = generate_restriction(request, child, xml_tree, full_path,
                                                      edit_data_tree=edit_data_tree, schema_location=schema_location)

            form_string += restriction_result[0]
            db_element['children'].append(restriction_result[1])
        elif child.tag == "{0}extension".format(LXML_SCHEMA_NAMESPACE):
            extension_result = generate_extension(request, child, xml_tree, full_path,
                                                  edit_data_tree=edit_data_tree, schema_location=schema_location)

            form_string += extension_result[0]
            db_element['children'].append(extension_result[1])

    return form_string


def generate_module(request, element, xsd_xpath=None, xml_xpath=None, xml_tree=None, edit_data_tree=None):
    """Generate a module to replace an element

    Parameters:
        request:
        element:
        xsd_xpath:
        xml_xpath:
        edit_data_tree:

    Returns:
        Module
    """
    form_string = ""
    reload_data = None
    reload_attrib = None

    if request.session['curate_edit']:
        # get the schema namespaces
        xml_tree_str = etree.tostring(xml_tree)
        namespaces = common.get_namespaces(BytesIO(str(xml_tree_str)))
        edit_elements = edit_data_tree.xpath(xml_xpath, namespaces=namespaces)
        
        if len(edit_elements) > 0:
            if len(edit_elements) == 1:
                edit_element = edit_elements[0]

                # get attributes
                if 'attribute' not in xsd_xpath and len(edit_element.attrib) > 0:
                    reload_attrib = dict(edit_element.attrib)

                reload_data = get_xml_element_data(element, edit_element)
            else:
                reload_data = []
                reload_attrib = []

                for edit_element in edit_elements:
                    reload_attrib.append(dict(edit_element.attrib))
                    reload_data.append(get_xml_element_data(element, edit_element))

    # check if a module is set for this element
    if '{http://mdcs.ns}_mod_mdcs_' in element.attrib:
        # get the url of the module
        url = element.attrib['{http://mdcs.ns}_mod_mdcs_']

        # check that the url is registered in the system
        if url in Module.objects.all().values_list('url'):
            view = get_module_view(url)

            # build a request to send to the module to initialize it
            mod_req = request
            mod_req.method = 'GET'

            mod_req.GET = {
                'url': url,
                'xsd_xpath': xsd_xpath,
                'xml_xpath': xml_xpath,
            }

            # if the loaded doc has data, send them to the module for initialization
            if reload_data is not None:
                mod_req.GET['data'] = reload_data

            if reload_attrib is not None:
                mod_req.GET['attributes'] = reload_attrib

            # renders the module
            form_string += view(mod_req).content.decode("utf-8")

    return form_string


def generate_simple_content(request, element, xml_tree, full_path, edit_data_tree=None, schema_location=None):
    """Generates a section of the form that represents an XML simple content

    Parameters:
        request:
        element:
        xml_tree:
        full_path:
        edit_data_tree:

    Returns:
        HTML string representing a simple content
    """
    # (annotation?,(restriction|extension))
    # FIXME better support for extension

    form_string = ""
    db_element = {
        'tag': 'simple_content',
        'value': None,
        'children': []
    }

    # remove the annotations
    remove_annotations(element)

    # generates the content
    if len(list(element)) != 0:
        child = element[0]

        if child.tag == "{0}restriction".format(LXML_SCHEMA_NAMESPACE):
            restriction_result = generate_restriction(request, child, xml_tree, full_path,
                                                edit_data_tree=edit_data_tree, schema_location=schema_location)

            form_string += restriction_result[0]
            db_element['children'].append(restriction_result[1])
        elif child.tag == "{0}extension".format(LXML_SCHEMA_NAMESPACE):
            extension_result = generate_extension(request, child, xml_tree, full_path,
                                              edit_data_tree=edit_data_tree, schema_location=schema_location)

            form_string += extension_result[0]
            db_element['children'].append(extension_result[1])

    return form_string, db_element


def generate_restriction(request, element, xml_tree, full_path="", edit_data_tree=None,
                         default_value=None, schema_location=None):
    """Generates a section of the form that represents an XML restriction

    Parameters:
        request:
        element: XML element
        xml_tree: XML Tree
        full_path:
        edit_data_tree:

    Returns:
        HTML string representing a sequence
    """
    # FIXME doesn't represent all the possibilities (http://www.w3schools.com/xml/el_restriction.asp)
    # FIXME simpleType is a possible child only if the base attr has not been specified
    form_string = ""
    db_element = {
        'tag': 'restriction',
        'options': {
            'base': element.attrib.get('base')  # TODO Change it to avoid having the namespace with it
        },
        'value': None,
        'children': []
    }

    remove_annotations(element)

    enumeration = element.findall('{0}enumeration'.format(LXML_SCHEMA_NAMESPACE))

    if len(enumeration) > 0:
        option_list = []

        if request.session['curate_edit']:
            default_value = default_value if default_value is not None else ''
            for enum in enumeration:
                db_child = {
                    'tag': 'enumeration',
                    'value': enum.attrib.get('value')
                }

                if default_value is not None and enum.attrib.get('value') == default_value:
                    entry = (enum.attrib.get('value'), enum.attrib.get('value'), True)
                    # db_child['tag'] = 'enumeration/selected'
                    db_element['value'] = default_value
                else:
                    entry = (enum.attrib.get('value'), enum.attrib.get('value'), False)

                option_list.append(entry)
                db_element['children'].append(db_child)
        else:
            for enum in enumeration:
                db_child = {
                    'tag': 'enumeration',
                    'value': enum.attrib.get('value')
                }

                entry = (enum.attrib.get('value'), enum.attrib.get('value'), False)
                option_list.append(entry)

                db_element['children'].append(db_child)

        form_string += render_select(None, option_list)
    else:
        simple_type = element.find('{0}simpleType'.format(LXML_SCHEMA_NAMESPACE))
        if simple_type is not None:
            simple_type_result = generate_simple_type(request, simple_type, xml_tree, full_path=full_path,
                                                edit_data_tree=edit_data_tree, default_value=default_value,
                                                schema_location=schema_location)

            form_string += simple_type_result[0]
            db_child = simple_type_result[1]
        else:
            form_string += render_input(default_value, '', '')
            db_child = {
                'tag': 'input',
                'value': default_value
            }

        db_element['children'].append(db_child)

    return form_string, db_element

# TODO: commented extensions Registry
# def get_extensions(request, xml_doc_tree, default_prefix):
#     """Get all XML extensions of the XML Schema
#
#     Parameters:
#         request:
#         element:
#         xml_tree:
#         full_path:
#         edit_data_tree:
#
#     Returns:
#         HTML string representing an extension
#     """
#     # get all extensions of the document
#     extensions = xml_doc_tree.findall(".//{0}extension".format(LXML_SCHEMA_NAMESPACE))
#     # keep only simple/complex type extensions, no built-in types
#     custom_type_extensions = {}
#     for extension in extensions:
#         base = extension.attrib['base']
#         if base not in common.getXSDTypes(default_prefix):
#             if base not in custom_type_extensions.keys():
#                 custom_type_extensions[base] = []
#             custom_type_extensions[base].append(etree.ElementTree(xml_doc_tree).getpath(extension))
#
#     return custom_type_extensions


def generate_extension(request, element, xml_tree, full_path="", edit_data_tree=None, schema_location=None):
    """Generates a section of the form that represents an XML extension

    Parameters:
        request:
        element:
        xml_tree:
        full_path:
        edit_data_tree:

    Returns:
        HTML string representing an extension
    """
    # FIXME doesn't represent all the possibilities (http://www.w3schools.com/xml/el_extension.asp)
    form_string = ""
    db_element = {
        'tag': 'extension',
        'value': None,
        'children': []
    }

    remove_annotations(element)

    ##################################################
    # Parsing attributes
    #
    # 'base' (required) is the only attribute to parse
    ##################################################
    if 'base' in element.attrib:
        base = element.attrib['base']

        xml_tree_str = etree.tostring(xml_tree)
        namespaces = common.get_namespaces(BytesIO(str(xml_tree_str)))
        default_prefix = common.get_default_prefix(namespaces)

        # test if base is a built-in data types
        if base in common.getXSDTypes(default_prefix):
            # TODO Get default value from the element
            if request.session['curate_edit']:
                elem = edit_data_tree.xpath(full_path)[0]
                default_value = elem.text
            else:
                default_value = ''

            db_element['children'].append(
                {
                    'tag': 'input',
                    'value': default_value
                }
            )
        else:  # not a built-in data type
            if ':' in base:
                splitted_base = base.split(":")
                # base_ns_prefix = splitted_base[0]
                base_name = splitted_base[1]
                # namespaces = request.session['namespaces']
                # TODO: look at namespaces, target namespaces
                # base_ns = namespaces[baseNSPrefix]
                # base_ns = namespace
            else:
                base_name = base
                # base_ns = namespace

            # test if base is a simple type
            baseType = xml_tree.find(".//{0}simpleType[@name='{1}']".format(LXML_SCHEMA_NAMESPACE, base_name))
            if baseType is not None:
                simple_type_result = generate_simple_type(request, baseType, xml_tree, full_path,
                                                    edit_data_tree, schema_location=schema_location)

                form_string += simple_type_result[0]
                db_element['children'].append(simple_type_result[1])
            else:
                # test if base is a complex type
                baseType = xml_tree.find(".//{0}complexType[@name='{1}']".format(LXML_SCHEMA_NAMESPACE, base_name))
                if baseType is not None:
                    complex_type_result = generate_complex_type(request, baseType, xml_tree, full_path,
                                                         edit_data_tree, schema_location=schema_location)

                    form_string += complex_type_result[0]
                    db_element['children'].append(complex_type_result[1])

    ##################################################
    # Parsing children
    #
    ##################################################
    if 'children' in db_element['children'][0]: # Element extends simple or complex type
        extended_element = db_element['children'][0]['children']
    else:  # Element extends one of the base types
        extended_element = db_element['children']

    # does it contain any attributes?
    complexTypeChildren = element.findall('{0}attribute'.format(LXML_SCHEMA_NAMESPACE))
    if len(complexTypeChildren) > 0:
        for attribute in complexTypeChildren:
            element_result = generate_element(request, attribute, xml_tree, full_path=full_path,
                                            edit_data_tree=edit_data_tree, schema_location=schema_location)

            form_string += element_result[0]
            extended_element.append(element_result[1])

    # does it contain sequence or all?
    complexTypeChild = element.find('{0}sequence'.format(LXML_SCHEMA_NAMESPACE))
    if complexTypeChild is not None:
        sequence_result = generate_sequence(request, complexTypeChild, xml_tree, full_path=full_path,
                                         edit_data_tree=edit_data_tree, schema_location=schema_location)

        form_string += sequence_result[0]
        extended_element.append(sequence_result[1])
    else:
        complexTypeChild = element.find('{0}all'.format(LXML_SCHEMA_NAMESPACE))
        if complexTypeChild is not None:
            sequence_result = generate_sequence(request, complexTypeChild, xml_tree, full_path=full_path,
                                             edit_data_tree=edit_data_tree, schema_location=schema_location)

            form_string += sequence_result[0]
            extended_element.append(sequence_result[1])
        else:
            # does it contain choice ?
            complexTypeChild = element.find('{0}choice'.format(LXML_SCHEMA_NAMESPACE))
            if complexTypeChild is not None:
                choice_result = generate_choice(request, complexTypeChild, xml_tree, full_path=full_path,
                                               edit_data_tree=edit_data_tree, schema_location=schema_location)

                form_string += choice_result[0]
                extended_element.append(choice_result[1])

    return form_string, db_element
