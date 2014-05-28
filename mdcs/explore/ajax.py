################################################################################
#
# File Name: ajax.py
# Application: explore
# Purpose:   
#
# Author: Sharief Youssef
#         sharief.youssef@nist.gov
#
#        Guillaume Sousa Amaral
#        guillaume.sousa@nist.gov
#
# Sponsor: National Institute of Standards and Technology (NIST)
#
################################################################################

import re
from django.utils import simplejson
from dajax.core import Dajax
from dajaxice.decorators import dajaxice_register
from django.conf import settings
from mongoengine import *
from explore.models import XMLSchema 
from io import BytesIO
from lxml import html
from collections import OrderedDict
from pymongo import Connection
import xmltodict

#import xml.etree.ElementTree as etree
import lxml.etree as etree
import xml.dom.minidom as minidom
from _winreg import QueryValue

# Global Variables
xmlString = ""
xmlDocTree = ""
formString = ""
customFormString = ""
queryBuilderString = ""
savedQueryForm = ""
mapTagIDElementInfo = None
mapQueryInfo = dict()
mapCriterias = OrderedDict()
mapEnumIDChoices = dict()
debugON = 0
nbChoicesID = 0
defaultPrefix = ""
defaultNamespace = ""



results = []

# Class definition
class Template(Document):
    title = StringField(required=True)
    filename = StringField(required=True)
    content = StringField(required=True)
    
class queryResults(Document):
    results = ListField(required=True)
    
class SavedQuery(Document):
    user = StringField(required=True)
    template = StringField(required=True)    
    query = StringField(required=True)
    displayedQuery = StringField(required=True)
    ListRegex = ListField()
    ListPattern = ListField()

def postprocessor(path, key, value):
        try:
            return key, int(value)        
        except (ValueError, TypeError):
            try:
                return key, float(value)
            except (ValueError, TypeError):
                return key, value  
    
class XMLData():
    """
        Wrapper to manage JSON Documents, like mongoengine would have manage them (but with ordered data)
    """
    
    def __init__(self, schema=None, xml=None, title=""):
        """
            initialize the object
            schema = ref schema (Document)
            xml = xml string
        """        
        # create a connection
        connection = Connection()
        # connect to the db 'mgi'
        db = connection['mgi']
        # get the jsonDoc collection
        self.xmldata = db['xmldata']
        # create a new dict to keep the mongoengine order
        self.content = OrderedDict()
        # insert the ref to schema
        self.content['schema'] = schema.id
        #insert the title
        self.content['title'] = title
        # insert the json content after
        self.content.update(xmltodict.parse(xml, postprocessor=postprocessor))
        
    def save(self):
        """save into mongo db"""
        # insert the content into mongo db
        self.xmldata.insert(self.content)

        
    @staticmethod
    def objects():        
        """
            returns all objects as a list of dicts
             /!\ Doesn't return the same kind of objects as mongoengine.Document.objects()
        """
        # create a connection
        connection = Connection()
        # connect to the db 'mgi'
        db = connection['mgi']
        # get the xmldata collection
        xmldata = db['xmldata']
        # find all objects of the collection
        cursor = xmldata.find(as_class = OrderedDict)
        # build a list with the objects        
        results = []
        for result in cursor:
            results.append(result)
        return results

    

    @staticmethod
    def executeQuery(query):
        """queries mongo db and returns results data"""
        # create a connection
        connection = Connection()
        # connect to the db 'mgi'
        db = connection['mgi']
        # get the xmldata collection
        xmldata = db['xmldata']
        # query mongo db
        cursor = xmldata.find(query,as_class = OrderedDict)  
        # build a list with the xml representation of objects that match the query      
        queryResults = []
        for result in cursor:
            queryResults.append(result['content'])
        return queryResults
    
class ElementInfo:    
    def __init__(self, type="", path=""):
        self.type = type
        self.path = path
        
class CriteriaInfo:
    def __init__(self, elementInfo=None, queryInfo=None):
        self.elementInfo = elementInfo
        self.queryInfo = queryInfo
        
class QueryInfo:
    def __init__(self, query="", displayedQuery=""):
        self.query = query
        self.displayedQuery = displayedQuery


################################################################################
# 
# Function Name: setCurrentTemplate(request)
# Inputs:        request - 
#                templateFilename -  
#                templateID - 
# Outputs:       JSON data with success or failure
# Exceptions:    None
# Description:   Set the current template to input argument.  Template is read into
#                an xsdDocTree for use later.
#
################################################################################
@dajaxice_register
def setCurrentTemplate(request,templateFilename, templateID):
    print 'BEGIN def setCurrentTemplate(request)'
    
    global xmlDocTree
    global xmlString
    global formString
    global customFormString

    # reset global variables
    xmlString = ""
    formString = ""
    customFormString = ""
    
    request.session['exploreCurrentTemplate'] = templateFilename
    request.session['exploreCurrentTemplateID'] = templateID
    request.session.modified = True
    print '>>>>' + templateFilename + ' set as current template in session'
    dajax = Dajax()

    templateObject = Template.objects.get(filename=templateFilename)
    xmlDocData = templateObject.content

    print XMLSchema.tree
    XMLSchema.tree = etree.parse(BytesIO(xmlDocData.encode('utf-8')))
    print XMLSchema.tree
    xmlDocTree = XMLSchema.tree

    print 'END def setCurrentTemplate(request)'
    return dajax.json()



################################################################################
# 
# Function Name: verifyTemplateIsSelected(request)
# Inputs:        request - 
# Outputs:       JSON data with templateSelected 
# Exceptions:    None
# Description:   Verifies the current template is selected.
# 
################################################################################
@dajaxice_register
def verifyTemplateIsSelected(request):
    print 'BEGIN def verifyTemplateIsSelected(request)'
    if 'exploreCurrentTemplate' in request.session:
        print 'template is selected'
        templateSelected = 'yes'
    else:
        print 'template is not selected'
        templateSelected = 'no'
#     dajax = Dajax()

    print 'END def verifyTemplateIsSelected(request)'
    return simplejson.dumps({'templateSelected':templateSelected})

################################################################################
# 
# Function Name: setCurrentModel(request,modelFilename)
# Inputs:        request - 
#                modelFilename - 
# Outputs:       JSON data 
# Exceptions:    None
# Description:   Sets current model 
# 
################################################################################
@dajaxice_register
def setCurrentModel(request,modelFilename):
    print 'BEGIN def setCurrentModel(request)'
    request.session['exploreCurrentTemplate'] = modelFilename
    request.session.modified = True
    print '>>>>' + modelFilename
    dajax = Dajax()

    print 'END def setCurrentModel(request)'
    return dajax.json()


################################################################################
# 
# Function Name: generateFormSubSection(xpath,selected,fullPath)
# Inputs:        xpath -
#                selected -
#                fullPath - 
# Outputs:       JSON data 
# Exceptions:    None
# Description:   
#
################################################################################
def generateFormSubSection(xpath,selected, fullPath):
    print 'BEGIN def generateFormSubSection(xpath,selected,fullPath)'
    formString = ""
    global xmlString
    global xmlDocTree
    global xmlDataTree
    global mapTagIDElementInfo
    global nbChoicesID
    global debugON
    global defaultNamespace
    global defaultPrefix
    
    
    
    p = re.compile('(\{.*\})?schema', re.IGNORECASE)

#     namespace = get_namespace(xmlDocTree.getroot())
#    xpathFormated = "./{0}element"
#    xpathFormated = "./{0}complexType[@name='"+xpath+"']"
    if xpath is None:
        print "xpath is none"
        return formString;

    xpathFormated = "./*[@name='"+xpath+"']"
    if debugON: formString += "xpathFormated: " + xpathFormated.format(defaultNamespace)
    e = xmlDocTree.find(xpathFormated.format(defaultNamespace))

    if e is None:
        return formString

    if e.tag == "{0}complexType".format(defaultNamespace):
        if debugON: formString += "matched complexType" 
        print "matched complexType" + "<br>"
        complexTypeChild = e.find('*')

        if complexTypeChild is None:
            return formString

        fullPath += "." + xpath
        if complexTypeChild.tag == "{0}sequence".format(defaultNamespace):
            if debugON: formString += "complexTypeChild:" + complexTypeChild.tag + "<br>"
            sequenceChildren = complexTypeChild.findall('*')            
            for sequenceChild in sequenceChildren:
                if debugON: formString += "SequenceChild:" + sequenceChild.tag + "<br>"
                print "SequenceChild: " + sequenceChild.tag 
                if sequenceChild.tag == "{0}element".format(defaultNamespace):
                    if 'type' not in sequenceChild.attrib:
                        pass
#                         if 'ref' in sequenceChild.attrib:
#                             if sequenceChild.attrib.get('ref') == "hdf5:HDF5-File":
#                                 formString += "<ul><li><i><div id='hdf5File'>" + sequenceChild.attrib.get('ref') + "</div></i> "
#                                 formString += "<div class=\"btn select-element\" onclick=\"selectHDF5File('hdf5:HDF5-File',this);\"><i class=\"icon-folder-open\"></i> Select HDF5 File</div>"
#                                 formString += "</li></ul>"
#                             elif sequenceChild.attrib.get('ref') == "hdf5:Field":
#                                 formString += "<ul><li><i><div id='hdf5Field'>" + sequenceChild.attrib.get('ref') + "</div></i> "
#                                 formString += "</li></ul>"
                    elif (sequenceChild.attrib.get('type') == "{0}:string".format(defaultPrefix)
                          or sequenceChild.attrib.get('type') == "{0}:double".format(defaultPrefix)
                          or sequenceChild.attrib.get('type') == "{0}:integer".format(defaultPrefix)
                          or sequenceChild.attrib.get('type') == "{0}:anyURI".format(defaultPrefix)):                                                                
                        textCapitalized = sequenceChild.attrib.get('name')[0].capitalize()  + sequenceChild.attrib.get('name')[1:]                        
                        elementID = len(mapTagIDElementInfo.keys())
                        formString += "<ul><li id='" + str(elementID) + "'><nobr>" + textCapitalized + " <input type='checkbox'>" 
                        xmlString += "<" + sequenceChild.attrib.get('name') + ">" + "</" + sequenceChild.attrib.get('name') + ">"                        
                        formString += "</nobr></li></ul>"                    
                        elementInfo = ElementInfo(sequenceChild.attrib.get('type'),fullPath[1:] + "." + textCapitalized)
                        mapTagIDElementInfo[elementID] = elementInfo
                    else:                        
                        textCapitalized = sequenceChild.attrib.get('name')[0].capitalize()  + sequenceChild.attrib.get('name')[1:]    
                        elementID = len(mapTagIDElementInfo.keys())                        
                        isEnum = False
                        # look for enumeration
                        childElement = xmlDocTree.find("./*[@name='"+sequenceChild.attrib.get('type')+"']".format(defaultNamespace))
                        if (childElement is not None):
                            if(childElement.tag == "{0}simpleType".format(defaultNamespace)):
                                restrictionChild = childElement.find("{0}restriction".format(defaultNamespace))        
                                if restrictionChild is not None:                                    
                                    enumChildren = restrictionChild.findall("{0}enumeration".format(defaultNamespace))
                                    if enumChildren is not None:
                                        formString += "<ul><li id='" + str(elementID) + "'><nobr>" + textCapitalized + " <input type='checkbox'>" + "</nobr></li></ul>"
                                        elementInfo = ElementInfo("enum",fullPath[1:]+"." + textCapitalized)
                                        mapTagIDElementInfo[elementID] = elementInfo
                                        listChoices = []
                                        for enumChild in enumChildren:
                                            listChoices.append(enumChild.attrib['value'])
                                        mapEnumIDChoices[elementID] = listChoices
                                        isEnum = True
                                
                        if(isEnum is not True):                            
                            formString += "<ul><li><nobr>" + textCapitalized + " "
                            xmlString += "<" + sequenceChild.attrib.get('name') + ">"  
                            formString += generateFormSubSection(sequenceChild.attrib.get('type'),selected,fullPath)
                            xmlString += "</" + sequenceChild.attrib.get('name') + ">"
                            formString += "</nobr></li></ul>"                        
                elif sequenceChild.tag == "{0}choice".format(defaultNamespace):
                    chooseID = nbChoicesID
                    chooseIDStr = 'choice' + str(chooseID)
                    nbChoicesID += 1
                    formString += "<ul><li><nobr>Choose <select id='"+ chooseIDStr +"' onchange=\"changeChoice(this);\">"
                    choiceChildren = sequenceChild.findall('*')
                    selectedChild = choiceChildren[0]
                    xmlString += "<" + selectedChild.attrib.get('name') + "/>"
                    for choiceChild in choiceChildren:
                        if choiceChild.tag == "{0}element".format(defaultNamespace):
                            textCapitalized = choiceChild.attrib.get('name')[0].capitalize()  + choiceChild.attrib.get('name')[1:]
                            formString += "<option value='" + textCapitalized + "'>" + textCapitalized + "</option></b><br>"
                    formString += "</select>"
                    print "+++++++++++++++++++++++++++++++++++++++++++"
                    if selected == "":
                        for (counter, choiceChild) in enumerate(choiceChildren):
                            if choiceChild.tag == "{0}element".format(defaultNamespace):
                                if choiceChild.attrib.get('type') != "{0}:string".format(defaultPrefix):
                                    textCapitalized = choiceChild.attrib.get('name')[0].capitalize()  + choiceChild.attrib.get('name')[1:]
                                    print textCapitalized + " is not string type"
                                    if (counter > 0):
#                                         formString += "<ul id=\"" + textCapitalized + "\" style=\"display:none;\"><li><nobr>" + textCapitalized
                                        formString += "<ul id=\"" + chooseIDStr + "-" + str(counter) + "\" style=\"display:none;\"><li><nobr>" + textCapitalized
                                    else:
#                                         formString += "<ul id=\"" + textCapitalized + "\"><li><nobr>" + textCapitalized
                                        formString += "<ul id=\""  + chooseIDStr + "-" + str(counter) + "\"><li><nobr>" + textCapitalized
                                    xmlString += "<" + textCapitalized + ">" 
                                    formString += generateFormSubSection(choiceChild.attrib.get('type'),selected, fullPath) + "</nobr></li></ul>"
                                    xmlString += "</" + textCapitalized + ">"
                                else:
                                    textCapitalized = choiceChild.attrib.get('name')[0].capitalize()  + choiceChild.attrib.get('name')[1:]
                                    print textCapitalized + " is string type"
                                    formString += "<ul><li><nobr>" + choiceChild.attrib.get('name').capitalize() + " <input type='checkbox'>" + "</nobr></li></ul>"
                    else:
                        formString += "selected not empty"
                    formString += "</nobr></li></ul>"
        elif complexTypeChild.tag == "{0}choice".format(defaultNamespace):
            if debugON: formString += "complexTypeChild:" + complexTypeChild.tag + "<br>"
            chooseID = nbChoicesID        
            chooseIDStr = 'choice' + str(chooseID)
            nbChoicesID += 1
            formString += "<ul><li><nobr>Choose <select id='"+ chooseIDStr +"' onchange=\"changeChoice(this);\">"        
            choiceChildren = complexTypeChild.findall('*')
            selectedChild = choiceChildren[0]
            xmlString += "<" + selectedChild.attrib.get('name') + "/>"
            for choiceChild in choiceChildren:
                if choiceChild.tag == "{0}element".format(defaultNamespace):
                    textCapitalized = choiceChild.attrib.get('name')[0].capitalize()  + choiceChild.attrib.get('name')[1:]
                    formString += "<option value='" + textCapitalized + "'>" + textCapitalized + "</option></b><br>"
            formString += "</select>"
            if selected == "":
                for (counter, choiceChild) in enumerate(choiceChildren):
                    if choiceChild.tag == "{0}element".format(defaultNamespace):
                        if choiceChild.attrib.get('type') != "{0}:string".format(defaultPrefix):
                            textCapitalized = choiceChild.attrib.get('name')[0].capitalize()  + choiceChild.attrib.get('name')[1:]
                            if (counter > 0):
#                                 formString += "<ul id=\"" + textCapitalized + "\" style=\"display:none;\"><li><nobr>" + textCapitalized
                                formString += "<ul id=\"" + chooseIDStr + "-" + str(counter) + "\" style=\"display:none;\"><li><nobr>" + textCapitalized
                            else:
#                                 formString += "<ul id=\"" + textCapitalized + "\"><li><nobr>" + textCapitalized
                                formString += "<ul id=\""  + chooseIDStr + "-" + str(counter) + "\"><li><nobr>" + textCapitalized
                            xmlString += "<" + textCapitalized + ">"     
                            # TODO : add tag ID and save choices if enum                                                                                
                            formString += generateFormSubSection(choiceChild.attrib.get('type'),selected, fullPath) + "</nobr></li></ul>"
                            xmlString += "</" + textCapitalized + ">"
                        else:
                            textCapitalized = choiceChild.attrib.get('name').capitalize()
                            elementID = len(mapTagIDElementInfo.keys())
                            formString += "<ul id=\"" + chooseIDStr + "-" + str(counter) + "\"><li id='" + str(elementID) + "'><nobr>" + textCapitalized + " <input type='checkbox'>" + "</nobr></li></ul>"                                      
                            elementInfo = ElementInfo(choiceChild.attrib.get('type'),fullPath[1:]+"." + textCapitalized)
                            mapTagIDElementInfo[elementID] = elementInfo
            else:
                formString += "selected not empty"
            formString += "</nobr></li></ul>"
        elif complexTypeChild.tag == "{0}attribute".format(defaultNamespace):
            textCapitalized = complexTypeChild.attrib.get('name')[0].capitalize()  + complexTypeChild.attrib.get('name')[1:]
            formString += "<li>" + textCapitalized + "</li>"
            xmlString += "<" + textCapitalized + ">" 
            xmlString += "</" + textCapitalized + ">"
    elif e.tag == "{0}simpleType".format(defaultNamespace):
        if debugON: formString += "matched simpleType" + "<br>"

        simpleTypeChildren = e.findall('*')
        
        if simpleTypeChildren is None:
            return formString

        for simpleTypeChild in simpleTypeChildren:
            if simpleTypeChild.tag == "{0}restriction".format(defaultNamespace):
                choiceChildren = simpleTypeChild.findall('*')
                for choiceChild in choiceChildren:
                    if choiceChild.tag == "{0}enumeration".format(defaultNamespace):
                        formString += "<input type='checkbox'>"
                        break

    print 'END def generateFormSubSection(xpath,selected,fullPath)'
    return formString

################################################################################
# 
# Function Name: generateForm(key)
# Inputs:        key -
# Outputs:       rendered HTMl form
# Exceptions:    None
# Description:   Renders HTMl form for display.
#
################################################################################

def generateForm(key):
    print 'BEGIN def generateForm(key)'
    formString = ""
    global xmlString
    global xmlDocTree
    global mapTagIDElementInfo
    global nbChoicesID
    global defaultNamespace
    global defaultPrefix

    mapTagIDElementInfo = dict()
    nbChoicesID = 0

    defaultNamespace = "http://www.w3.org/2001/XMLSchema"
    for prefix, url in xmlDocTree.getroot().nsmap.iteritems():
        if (url == defaultNamespace):            
            defaultPrefix = prefix
            break
    defaultNamespace = "{" + defaultNamespace + "}"
    if debugON: formString += "namespace: " + defaultNamespace + "<br>"
    e = xmlDocTree.findall("./{0}element".format(defaultNamespace))

    if debugON: e = xmlDocTree.findall("{0}complexType/{0}choice/{0}element".format(defaultNamespace))
    if debugON: formString += "list size: " + str(len(e))

    if len(e) > 1:
        formString += "<b>" + e[0].attrib.get('name').capitalize() + "</b><br><ul><li>Choose:"
        for i in e:
            formString += "more than one: " + i.tag + "<br>"
    else:
        textCapitalized = e[0].attrib.get('name')[0].capitalize()  + e[0].attrib.get('name')[1:]
        formString += "<b>" + textCapitalized + "</b><br>"
        if debugON: xmlString += "<" + textCapitalized + ">"
        xmlString += "<" + e[0].attrib.get('name') + ">"
        if debugON: formString += "<b>" + e[0].attrib.get('name').capitalize() + "</b><br>"
        formString += generateFormSubSection(e[0].attrib.get('type'),"", "")
        if debugON: xmlString += "</" + textCapitalized + ">"
        xmlString += "</" + e[0].attrib.get('name') + ">"
       
    # pretty string
#    s = etree.tostring(xmlDataTree) #, pretty_print=True)
#    print "xmlDataTree:\n" + s

    print 'END def generateForm(key)'

    return formString

################################################################################
# 
# Function Name: generateXSDTreeForQueryingData(request)
# Inputs:        request - 
# Outputs:       
# Exceptions:    None
# Description:   
#
################################################################################
@dajaxice_register
def generateXSDTreeForQueryingData(request): 
    print 'BEGIN def generateXSDTreeForQueryingData(request)'

    global xmlString
    global formString
    global xmlDocTree
    global xmlDataTree

    dajax = Dajax()
    templateFilename = request.session['exploreCurrentTemplate']
    templateID = request.session['exploreCurrentTemplateID']
    print '>>>> ' + templateFilename + ' is the current template in session'
    
    if xmlDocTree == "":
        setCurrentTemplate(request,templateFilename, templateID)
    if (formString == ""):
        xmlString = ""
        formString = "<form id=\"dataQueryForm\" name=\"xsdForm\">"
        formString += generateForm("schema")        
        reparsed = minidom.parseString(xmlString)
        formString += "</form>"        
    
    dajax.assign('#xsdForm', 'innerHTML', formString)
 
    print 'END def generateXSDTreeForQueryingData(request)'
    return dajax.json()

################################################################################
# 
# Function Name: changeXMLSchema(request,operation,xpath,name)
# Inputs:        request - 
#                operation - 
#                xpath - 
#                name - 
# Outputs:       
# Exceptions:    None
# Description:   
#
################################################################################
# @dajaxice_register
# def changeXMLSchema(request,operation,xpath,name):
#     print 'BEGIN def changeXMLSchema(request,operation,xpath,name)'
#     dajax = Dajax()
# 
#     global xmlString
#     global xmlDocTree
# 
#     print "operation: " + operation
#     print "xpath: " + xpath
#     print "name: " + name
# 
# 
#     if xmlDocTree == "":
#         print "xmlDocTree is null"
#         templateFilename = request.session['exploreCurrentTemplate']
#         pathFile = "{0}/mdcs/xsdfiles/" + templateFilename
#         path = pathFile.format(
#             settings.SITE_ROOT)
#         xmlDocTree = etree.parse(path)
#         generateXSDTreeForQueryingData(request)
#     else:
#         print "xmlDocTree is not null"
# 
#     root = xmlDocTree.getroot()
#     namespace = get_namespace(xmlDocTree.getroot())
# 
#     namespace = namespace[1:-1]
# 
#     print "root:"
#     print root
#     print "namespace: " + namespace
# 
#     e = xmlDocTree.xpath(xpath,namespaces={'xsd':namespace})
# 
#     print e[0].attrib.get('occurances')
#     occurances = int(e[0].attrib.get('occurances'))
#     if operation == "add":
#         occurances += 1
#     else:
#         if occurances > 0:
#             occurances -= 1
#     print occurances
#     e[0].attrib['occurances'] = str(occurances)
#     
#     formString = "<br><form id=\"dataQueryForm\">"
#     formString += generateForm("schema")
#     formString += "</form>"
#     dajax.assign('#xsdForm', 'innerHTML', formString)
# 
#     
#     print 'END def changeXMLSchema(request,operation,xpath,name)'
#     return dajax.json()


################################################################################
# 
# Function Name: executeQuery(request, queryForm, queryBuilder)
# Inputs:        request - 
#                queryForm - 
#                queryBuilder - 
# Outputs:       
# Exceptions:    None
# Description:   execute a query in mongo db
#
################################################################################
@dajaxice_register
def executeQuery(request, queryForm, queryBuilder):
    print 'BEGIN def executeQuery(request, queryForm, queryBuilder)'        
    dajax = Dajax()
    global results
    global queryBuilderString
    global savedQueryForm
    
    queryBuilderString = queryBuilder
    savedQueryForm = queryForm
    
    queryFormTree = html.fromstring(queryForm)
    errors = checkQueryForm(queryFormTree)
    if(len(errors)== 0):
        htmlTree = html.fromstring(queryForm)
        query = fieldsToQuery(htmlTree)
        results = XMLData.executeQuery(query)
        dajax.script("resultsCallback();")
    else:
        errorsString = ""
        for error in errors:
            errorsString += "<p>" + error + "</p>"            
        dajax.assign('#listErrors', 'innerHTML', errorsString)
        dajax.script("displayErrors();")

    print 'END def executeQuery(request, queryForm, queryBuilder)'
    return dajax.json()


################################################################################
# 
# Function Name: getResults(request)
# Inputs:        request -  
# Outputs:       
# Exceptions:    None
# Description:   Get results of a query
#
################################################################################
@dajaxice_register
def getResults(request):
    print 'BEGIN def getResults(request)'
    dajax = Dajax()
    global results
    
    resultString = ""
    
    if len(results) > 0 :
        for result in results:
            resultString += "<textarea class='xmlResult' readonly='true'>"  
            resultString += str(xmltodict.unparse(result, pretty=True))
            resultString += "</textarea> <br/>"
    else:
        resultString = "<span style='font-style:italic; color:red;'> No Results found... </span>"
            
    dajax.assign("#results", "innerHTML", resultString)
    
    print 'END def getResults(request)'
    return dajax.json()


################################################################################
# 
# Function Name: intCriteria(path, comparison, value, isNot=False)
# Inputs:        path - 
#                comparison -
#                value -
#                isNot -
# Outputs:       a criteria
# Exceptions:    None
# Description:   Build a criteria for mongo db for the type integer
#
################################################################################
def intCriteria(path, comparison, value, isNot=False):
    print 'BEGIN def intCriteria(path, comparison, value, isNot=False)'
    criteria = dict()

    if(comparison == "="):
        if(isNot):
            criteria[path] = eval('{"$ne":' + value + '}')
        else:
            criteria[path] = int(value)
    else:
        if(isNot):
            criteria[path] = eval('{"$not":{"$' +comparison+ '":'+ value +'}}')
        else:
            criteria[path] = eval('{"$'+comparison+'":'+ value +'}')

    print 'END def intCriteria(path, comparison, value, isNot=False)'
    return criteria

def floatCriteria(path, comparison, value, isNot=False):
    criteria = dict()

    if(comparison == "="):
        if(isNot):
            criteria[path] = eval('{"$ne":' + value + '}')
        else:
            criteria[path] = float(value)
    else:
        if(isNot):
            criteria[path] = eval('{"$not":{"$' +comparison+ '":'+ value +'}}')
        else:
            criteria[path] = eval('{"$'+comparison+'":'+ value +'}')

    return criteria

def stringCriteria(path, comparison, value, isNot=False):
    criteria = dict()
    
    if (comparison == "is"):
        if(isNot):
            criteria[path] = eval('{"$ne":' + repr(value) + '}')
        else:
            criteria[path] = str(value)
    elif (comparison == "like"):
        if(isNot):
            criteria[path] = dict()
            criteria[path]["$not"] = re.compile(value)
        else:
            criteria[path] = re.compile(value)
    
    return criteria

def queryToCriteria(query, isNot=False):
    if(isNot):
#         return eval('{"$not":' + str(query) + '}')
        return invertQuery(query.copy())
    else:
        return query

def invertQuery(query):
    for key, value in query.iteritems():
        if key == "$and" or key == "$or":
            for subValue in value:
                invertQuery(subValue)
#         elif key == "$not":        
#             query.update(value)
#             query.pop(key)
        else:            
            #lt, lte, =, gte, gt, not, ne
            if isinstance(value,dict):                
                if value.keys()[0] == "$not" or value.keys()[0] == "$ne":
                    query[key] = (value[value.keys()[0]])                    
                else:
                    savedValue = value
                    query[key] = dict()
                    query[key]["$not"] = savedValue
            else:
                savedValue = value
                if isinstance(value, re._pattern_type):
                    query[key] = dict()
                    query[key]["$not"] = savedValue
                else:
                    query[key] = dict()
                    query[key]["$ne"] = savedValue
    return query

def enumCriteria(path, value, isNot=False):
    criteria = dict()
    
    if(isNot):
        criteria[path] = eval('{"$ne":' + repr(value) + '}')
    else:
        criteria[path] = str(value)
            
    return criteria

def ANDCriteria(criteria1, criteria2):
#     return criteria1.update(criteria2)
    ANDcriteria = dict()
    ANDcriteria["$and"] = []
    ANDcriteria["$and"].append(criteria1)
    ANDcriteria["$and"].append(criteria2)
    return ANDcriteria

def ORCriteria(criteria1, criteria2):
    ORcriteria = dict()
    ORcriteria["$or"] = []
    ORcriteria["$or"].append(criteria1)
    ORcriteria["$or"].append(criteria2)
    return ORcriteria

def buildCriteria(elemPath, comparison, value, elemType, isNot=False):
    if (elemType == '{0}:integer'.format(defaultPrefix)):
        return intCriteria(elemPath, comparison, value, isNot)
    elif (elemType == '{0}:float'.format(defaultPrefix) or elemType == '{0}:double'.format(defaultPrefix)):
        return floatCriteria(elemPath, comparison, value, isNot)
    elif (elemType == '{0}:string'.format(defaultPrefix)):
        return stringCriteria(elemPath, comparison, value, isNot)
    else:
        return stringCriteria(elemPath, comparison, value, isNot)

def fieldsToQuery(htmlTree):
    fields = htmlTree.findall("./p")
    
    query = dict()
#     criteriaIterator = 0
    for field in fields:        
        boolComp = field[0].value
        if (boolComp == 'NOT'):
            isNot = True
        else:
            isNot = False
            
        elemType = mapCriterias[field.attrib['id']].elementInfo.type
        if (elemType == "query"):
            queryValue = mapCriterias[field.attrib['id']].queryInfo.query
#             criteriaIterator += 1
            criteria = queryToCriteria(queryValue, isNot)
        elif (elemType == "enum"):
            element = "content." + mapCriterias[field.attrib['id']].elementInfo.path
#             criteriaIterator += 1
            value = field[2][0].value            
            criteria = enumCriteria(element, value, isNot)
        else:                
            element = "content." + mapCriterias[field.attrib['id']].elementInfo.path
#             criteriaIterator += 1
            comparison = field[2][0].value
            value = field[2][1].value
            criteria = buildCriteria(element, comparison, value, elemType , isNot)
        
        if(boolComp == 'OR'):        
            query = ORCriteria(query, criteria)
        elif(boolComp == 'AND'):
            query = ANDCriteria(query, criteria)
        else:
            if(fields.index(field) == 0):
                query.update(criteria)
            else:
                query = ANDCriteria(query, criteria)
        
    return query


def checkQueryForm(htmlTree):
    global mapCriterias
    
    errors = []
    fields = htmlTree.findall("./p")
    if (len(mapCriterias) != len(fields)):
        errors.append("Some fields are empty !")
    else:
        for field in fields:
            elemType = mapCriterias[field.attrib['id']].elementInfo.type
            
            if (elemType == "{0}:float".format(defaultPrefix) or elemType == "{0}:double".format(defaultPrefix)):
                value = field[2][1].value
                try:
                    float(value)
                except ValueError:
                    elementPath = mapCriterias[field.attrib['id']].elementInfo.path
                    element = elementPath.split('.')[-1]
                    errors.append(element + " must be a number !")
                        
            elif (elemType == "{0}:integer".format(defaultPrefix)):
                value = field[2][1].value
                try:
                    int(value)
                except ValueError:
                    elementPath = mapCriterias[field.attrib['id']].elementInfo.path
                    element = elementPath.split('.')[-1]
                    errors.append(element + " must be an integer !")
                    
            elif (elemType == "{0}:string".format(defaultPrefix)):
                comparison = field[2][0].value
                value = field[2][1].value
                elementPath = mapCriterias[field.attrib['id']].elementInfo.path
                element = elementPath.split('.')[-1]
                if (comparison == "like"):
                    try:
                        re.compile(value)
                    except Exception, e:
                        errors.append(element + " must be a valid regular expression ! (" + str(e) + ")")
                    
    return errors
                    
                    
@dajaxice_register
def addField(request, htmlForm):
    dajax = Dajax()
    htmlTree = html.fromstring(htmlForm)
    
    fields = htmlTree.findall("./p")    
    fields[-1].remove(fields[-1].find("./span[@class='icon add']"))      
    if (len(fields) == 1):
        criteriaID = fields[0].attrib['id']
        minusButton = html.fragment_fromstring("""<span class="icon remove" onclick="removeField('""" + str(criteriaID) +"""')"></span>""")
        fields[0].append(minusButton)
    
    # get the id of the last field (get the value of the increment, remove crit)
    lastID = fields[-1].attrib['id'][4:]
    tagID = int(lastID) + 1
    element = html.fragment_fromstring("""
        <p id='crit""" + str(tagID) + """'>
        """
        +
            renderANDORNOT() 
        +
        """
            <input droppable="true" readonly="readonly" type="text" class="elementInput">     
            <span id='ui"""+ str(tagID) +"""'>
            </span>  
            <span class="icon remove" onclick="removeField('crit""" + str(tagID) + """')"></span>
            <span class="icon add" onclick="addField()"></span>
        </p>
    """)
    
    #insert before the 3 buttons (save, clear, execute)
    htmlTree.insert(-3,element)   
    
    dajax.assign("#queryForm", "innerHTML", html.tostring(htmlTree))
    
    dajax.script("""
        makeInputsDroppable();
    """);
    return dajax.json()

@dajaxice_register
def removeField(request, queryForm, criteriaID):
    dajax = Dajax()
    global mapCriterias
    
    htmlTree = html.fromstring(queryForm)
    
    currentElement = htmlTree.get_element_by_id(criteriaID)
    fields = htmlTree.findall("./p")
    
    
    # suppress last element => give the + to the previous
    if(fields[-1].attrib['id'] == criteriaID):
        plusButton = html.fragment_fromstring("""<span class="icon add" onclick="addField()"></span>""")
        fields[-2].append(plusButton)
    # only one element left => remove the -
    if(len(fields) == 2):
        fields[-1].remove(fields[-1].find("./span[@class='icon remove']"))
        fields[-2].remove(fields[-2].find("./span[@class='icon remove']"))
        
    htmlTree.remove(currentElement)
    
    # replace the bool of the first element by the 2 choices input (YES/NOT) if it was an element with 3 inputs (AND/OR/NOT)
    fields = htmlTree.findall("./p")
    if(len(fields[0][0].value_options) is not 2):
        if (fields[0][0].value == 'NOT'):
            fields[0][0] = html.fragment_fromstring(renderYESORNOT())
            fields[0][0].value = 'NOT'
        else:
            fields[0][0] = html.fragment_fromstring(renderYESORNOT())
        
    try:
        del mapCriterias[criteriaID]
    except:
        pass
    
    dajax.assign("#queryForm", "innerHTML", html.tostring(htmlTree))
    dajax.script("""
        makeInputsDroppable();
    """);
    return dajax.json()


def renderYESORNOT():
    return """
        <select style="margin-right:4px;">
          <option value=""></option>
          <option value="NOT">NOT</option>
        </select> 
    """

def renderANDORNOT():
    return """
    <select>
      <option value="AND">AND</option>
      <option value="OR">OR</option>
      <option value="NOT">NOT</option>
    </select> 
    """

def renderNumericSelect():
    return """
    <select style="width:50px">
      <option value="lt">&lt;</option>
      <option value="lte">&le;</option>
      <option value="=">=</option>
      <option value="gte">&ge;</option>
      <option value="gt">&gt;</option>
    </select> 
    """

def renderValueInput():
    return """
    <input style="margin-left:4px;" type="text" class="valueInput"/>
    """

def renderStringSelect():
    return """
    <select>
      <option value="is">is</option>
      <option value="like">like</option>                      
    </select> 
    """

def renderEnum(fromElementID):
    enum = "<select class='selectInput'>"
    listOptions = mapEnumIDChoices[int(fromElementID)]
    for option in listOptions:
        enum += "<option value='" + option + "'>" + option + "</option>"    
    enum += "</select>"
    return enum

def renderSelectForm(tagID):
    pass

def buildPrettyCriteria(elementName, comparison, value, isNot=False):
    prettyCriteria = ""
    
    if (isNot):
        prettyCriteria += "NOT("
        
    prettyCriteria += elementName
    if(comparison == "lt"):
        prettyCriteria += " &lt; "
    elif (comparison == "lte"):
        prettyCriteria += " &le; "
    elif (comparison == "="):
        prettyCriteria += "="
    elif (comparison == "gte"):
        prettyCriteria += " &ge; "
    elif (comparison == "gt"):
        prettyCriteria += " &gt; "
    elif (comparison == "is"):
        prettyCriteria += " is "
    elif (comparison == "like"):
        prettyCriteria += " like "
    
    prettyCriteria += str(value)        
    
    if(isNot):
        prettyCriteria += ")"
    
    return prettyCriteria

def queryToPrettyCriteria(queryValue, isNot):
    if(isNot):
        return "NOT(" + queryValue + ")"
    else:
        return queryValue
    
def enumToPrettyCriteria(element, value, isNot=False):
    if(isNot):
        return "NOT(" + str(element) + " is " + str(value) + ")"
    else:
        return str(element) + " is " + str(value)

def ORPrettyCriteria(query, criteria):
    return "(" + query + " OR " + criteria + ")"

def ANDPrettyCriteria(query, criteria):
    return "(" + query + " AND " + criteria + ")"

def fieldsToPrettyQuery(queryFormTree):
    fields = queryFormTree.findall("./p")
    
    query = ""
#     criteriaIterator = 0
    for field in fields:        
        boolComp = field[0].value
        if (boolComp == 'NOT'):
            isNot = True
        else:
            isNot = False
                
        elemType = mapCriterias[field.attrib['id']].elementInfo.type
        if (elemType == "query"):
            queryValue = mapCriterias[field.attrib['id']].queryInfo.displayedQuery
#             criteriaIterator += 1
            criteria = queryToPrettyCriteria(queryValue, isNot)
        elif (elemType == "enum"):
            elementPath = mapCriterias[field.attrib['id']].elementInfo.path
            element = elementPath.split('.')[-1]
#             criteriaIterator += 1
            value = field[2][0].value            
            criteria = enumToPrettyCriteria(element, value, isNot)
        else:                 
            elementPath = mapCriterias[field.attrib['id']].elementInfo.path
            element = elementPath.split('.')[-1]
#             criteriaIterator += 1
            comparison = field[2][0].value
            value = field[2][1].value
            criteria = buildPrettyCriteria(element, comparison, value, isNot)
        
        if(boolComp == 'OR'):        
            query = ORPrettyCriteria(query, criteria)
        elif(boolComp == 'AND'):
            query = ANDPrettyCriteria(query, criteria)
        else:
            if(fields.index(field) == 0):
                query += criteria
            else:
                query = ANDPrettyCriteria(query, criteria)
        
    return query    

@dajaxice_register
def saveQuery(request, queryForm, queriesTable):
    dajax = Dajax()
    queryFormTree = html.fromstring(queryForm)

    # Check that the user can save a query
    errors = []
    if '_auth_user_id' in request.session:
        userID = request.session['_auth_user_id']
        if 'exploreCurrentTemplateID' in request.session:
            templateID = request.session['exploreCurrentTemplateID'] 
        else:
            errors = ['You have to select a template before you can save queries (Step 1 : Select Template).']
    else:
        errors = ['You have to login to save a query.']
    
    if(len(errors)== 0): 
        # Check that the query is valid      
        errors = checkQueryForm(queryFormTree)
        if(len(errors)== 0):
            query = fieldsToQuery(queryFormTree)    
            displayedQuery = fieldsToPrettyQuery(queryFormTree) 
        
            #save the query in the data base
            connect('mgi')
            
            ListRegex = []
            ListPattern = []
            manageRegexBeforeSave(query, ListRegex, ListPattern)
            savedQuery = SavedQuery(str(userID),str(templateID), str(query),displayedQuery,ListRegex, ListPattern)
            savedQuery.save()
            
            #add the query to the table        
#             queriesTree = html.fromstring(queriesList)
#             queriesTable = queriesTree.find("./[@id=queriesTable]")
            queriesTableTree = html.fromstring(queriesTable)
    
#             linesInTable = queriesTable.findall("./tbody")
#             if (len(linesInTable) == 1): #th
#                 queryID = 0
#             else:
#                 queryID = int(linesInTable[-1][0].attrib['id'][5:]) + 1
#                 pass
#             mapQueryInfo[queryID] = QueryInfo(query, displayedQuery)
            mapQueryInfo[str(savedQuery.id)] = QueryInfo(query, displayedQuery)
            
            element = html.fragment_fromstring(renderSavedQuery(str(displayedQuery),savedQuery.id))
            queriesTableTree.find("./tbody").append(element)
            dajax.assign('#queriesTable', 'innerHTML', html.tostring(queriesTableTree))
        else:
            errorsString = ""
            for error in errors:
                errorsString += "<p>" + error + "</p>"            
            dajax.assign('#listErrors', 'innerHTML', errorsString)
            dajax.script("displayErrors();")
    else:
        errorsString = ""
        for error in errors:
            errorsString += "<p>" + error + "</p>"            
        dajax.assign('#listErrors', 'innerHTML', errorsString)
        dajax.script("displayErrors();")

    return dajax.json()


def manageRegexBeforeSave(query, ListRegex, ListPattern):
#     for key, value in query.iteritems():
#         if isinstance(value, dict):
#             manageRegexBeforeSave(value)
#         else:
#             if isinstance(value, re._pattern_type):
#                 query[key] = "re.compile(" + value.pattern + ")"
    for key, value in query.iteritems():
        if key == "$and" or key == "$or":
            for subValue in value:
                manageRegexBeforeSave(subValue, ListRegex, ListPattern)
        else:
            if isinstance(value, re._pattern_type):
                ListRegex.append(str(value))
                ListPattern.append(value.pattern)
#                 DictRegex[str(value).replace(".", "")] = value.pattern

@dajaxice_register
def deleteQuery(request, queriesTable, savedQueryID):
    dajax = Dajax()
    global mapQueryInfo
    
#     queriesTree = html.fromstring(queriesList)
#     queriesTable = queriesTree.find(".//table")
#     lineToDelete = queriesTable.find(".//tr/[@id='"+ savedQueryID +"']")
#     queriesTable.remove(lineToDelete)
    
    # finds all lines in the table exept the first one : headers
    queriesTableTree = html.fromstring(queriesTable)
    tr = queriesTableTree.find("./tbody/tr[@id='"+ savedQueryID +"']")
    if(tr is not None):
        # removes the row         
        queriesTableTree.find("./tbody").remove(tr)   
#     # finds all lines in the table exept the first one : headers
#     for tbody in queriesTableTree.findall('./tbody')[1:]:
#         tr = tbody.find("./tr/[@id='"+ savedQueryID +"']")
#         if(tr is not None):
#             # removes the row         
#             queriesTableTree.remove(tbody)   
#             break
    
    connect('mgi')
    SavedQuery(id=savedQueryID[5:]).delete()
    del mapQueryInfo[savedQueryID[5:]]
    
    dajax.assign("#queriesTable", "innerHTML", html.tostring(queriesTableTree))
    dajax.script(""" 
        makeInputsDroppable();    
    """);
    return dajax.json()
    
    
def renderSavedQuery(query, queryID):
    return """
        <tr id=query"""+ str(queryID) +""">
            <td><span class="icon add" onclick="addSavedQueryToForm('query"""+ str(queryID) +"""')"></span></td>
            <td>""" + query +  """</td>
            <td><span class="icon remove" onclick="deleteQuery('query"""+ str(queryID) +"""')"></span></td>
        </tr>
    """

def checkTypes(queryFormTree, errors):
    areTypesOK = True
      
    for criteria in queryFormTree.findall("./p"):
        type = mapCriterias[criteria.attrib['id']].elementInfo.type
        if (type == "integer"):
            try:
                int(criteria[2][1].value)
            except:
                errors.append(criteria[1].value + " must be of type : " + type)
        elif (type == "string"):
            pass
        elif (type == "double"):
            pass
        elif (type == "query"):
            pass
        
    return areTypesOK

@dajaxice_register
def updateUserInputs(request, htmlForm, fromElementID, toCriteriaID):   
    dajax = Dajax()
    global mapTagIDElementInfo
    
    mapCriterias[toCriteriaID] = CriteriaInfo()
    mapCriterias[toCriteriaID].elementInfo = mapTagIDElementInfo[int(fromElementID)]
    
    htmlTree = html.fromstring(htmlForm)
    currentCriteria = htmlTree.get_element_by_id(toCriteriaID)  
    
    try:
        currentCriteria[1].attrib['class'] = currentCriteria[1].attrib['class'].replace('queryInput','elementInput') 
    except:
        pass
    # criteria id = crit%d  
    criteriaIDIncr = toCriteriaID[4:]
    userInputs = currentCriteria.find("./span/[@id='ui"+ str(criteriaIDIncr) +"']")
    
    for element in userInputs.findall("*"):
        userInputs.remove(element) 
    
    if (mapCriterias[toCriteriaID].elementInfo.type == "{0}:integer".format(defaultPrefix) 
        or mapCriterias[toCriteriaID].elementInfo.type == "{0}:double".format(defaultPrefix)):
        form = html.fragment_fromstring(renderNumericSelect())
        inputs = html.fragment_fromstring(renderValueInput()) 
        userInputs.append(form)
        userInputs.append(inputs) 
    elif (mapCriterias[toCriteriaID].elementInfo.type == "enum"):
        form = html.fragment_fromstring(renderEnum(fromElementID))
        userInputs.append(form)
    else:
        form = html.fragment_fromstring(renderStringSelect())
        inputs = html.fragment_fromstring(renderValueInput())
        userInputs.append(form)
        userInputs.append(inputs)
        

#     userInputs.getparent()[1].attrib['class'] = "elementInput ui-droppable"
    
    dajax.assign("#queryForm", "innerHTML", html.tostring(htmlTree))
    dajax.script("""
        makeInputsDroppable();    
    """);
    return dajax.json()
    
    
@dajaxice_register
def addSavedQueryToForm(request, queryForm, savedQueryID):
    dajax = Dajax()
    queryTree = html.fromstring(queryForm)
    
    fields = queryTree.findall("./p")
    fields[-1].remove(fields[-1].find("./span[@class='icon add']"))      
    if (len(fields) == 1):
        criteriaID = fields[0].attrib['id']
        minusButton = html.fragment_fromstring("""<span class="icon remove" onclick="removeField('""" + str(criteriaID) +"""')"></span>""")
        fields[0].append(minusButton)
        
    lastID = fields[-1].attrib['id'][4:]
    query = mapQueryInfo[savedQueryID[5:]].displayedQuery
    if (len(fields)== 1 and fields[0][1].value == ""):
        queryTree.remove(fields[0])
        tagID = int(lastID)
        element = html.fragment_fromstring("""
        <p id='crit""" + str(tagID) + """'>
        """
        +
            renderYESORNOT() 
        +
        """
            <input droppable="true" readonly="readonly" type="text" class="queryInput" value=" """+ str(query) +""" ">     
            <span id="ui"""+ str(tagID) +"""">
            </span>              
            <span class="icon add" onclick=addField()> </span>
        </p>
        """)
    else:
        tagID = int(lastID) + 1
        element = html.fragment_fromstring("""
            <p id='crit""" + str(tagID) + """'>
            """
            +
                renderANDORNOT() 
            +
            """
                <input droppable="true" readonly="readonly" type="text" class="queryInput" value=" """+ str(query) +""" ">     
                <span id="ui"""+ str(tagID) +"""">
                </span>  
                <span class="icon remove" onclick="removeField('crit"""+ str(tagID) +"""')"></span>
                <span class="icon add" onclick="addField()"> </span>
            </p>
        """)  
#             break
    
    #insert before the 3 buttons (save, clear, execute)
    queryTree.insert(-3,element)
    
    mapCriterias['crit'+ str(tagID)] = CriteriaInfo()
    mapCriterias['crit'+ str(tagID)].queryInfo = mapQueryInfo[savedQueryID[5:]]
    mapCriterias['crit'+ str(tagID)].elementInfo = ElementInfo("query") 
    dajax.assign("#queryForm", "innerHTML", html.tostring(queryTree))
    dajax.script("""    
        makeInputsDroppable();    
    """);
    return dajax.json()
    

def renderInitialForm():
    return """
    <p id="crit0">
        <select>
          <option value=""></option>
          <option value="NOT">NOT</option>
        </select> 
        <input droppable="true" readonly="readonly" type="text" class="elementInput"/>
        <span id="ui0">
        </span>                        
        <span class="icon add" onclick="addField()"></span>                                
    </p>
    """

@dajaxice_register
def clearCriterias(request, queryForm):
    """ Reset Saved Criterias """
    dajax = Dajax()
    global mapCriterias
    
    # Load the criterias tree     
    queryTree = html.fromstring(queryForm)
    
    fields = queryTree.findall("./p")
    for field in fields:
        queryTree.remove(field)
    
    initialForm = html.fragment_fromstring(renderInitialForm())
    queryTree.insert(0,initialForm)  
    
    mapCriterias.clear()
      
    dajax.assign("#queryForm", "innerHTML", html.tostring(queryTree))
    dajax.script("""   
        makeInputsDroppable();    
    """);
    return dajax.json()
    
@dajaxice_register
def clearQueries(request, queriesTable):
    """ Reset Saved Queries """
    dajax = Dajax()
    
    global mapQueryInfo
    
    queriesTableTree = html.fromstring(queriesTable)
        
    # finds all lines in the table exept the first one : headers
    for tr in queriesTableTree.findall('./tbody/tr')[1:]:
        # removes existing rows         
        queriesTableTree.find("./tbody").remove(tr)    
    
    connect('mgi')
    for queryID in mapQueryInfo.keys():
        SavedQuery(id=queryID).delete()
            
    mapQueryInfo.clear()
    
        
        
    dajax.assign("#queriesTable", "innerHTML", html.tostring(queriesTableTree))
    # render table again     
    dajax.script("""  
        makeInputsDroppable();    
    """);
    return dajax.json()

@dajaxice_register
def getCustomForm(request):
    dajax = Dajax()
    
    global customFormString
    global mapQueryInfo
    
    #delete criterias if user comes from another page than results
    if 'keepCriterias' in request.session:
        del request.session['keepCriterias']
        dajax.assign("#queryForm", "innerHTML", savedQueryForm)
    else:
        mapCriterias.clear()
    
    #Get saved queries of an user
    mapQueryInfo.clear()
    if '_auth_user_id' in request.session and 'exploreCurrentTemplateID' in request.session:
        userID = request.session['_auth_user_id']
        templateID = request.session['exploreCurrentTemplateID']
        connect('mgi')
        userQueries = SavedQuery.objects(user=str(userID),template=str(templateID))
        queriesTable = html.fragment_fromstring(
            """<table>
                <tr>                    
                    <th width="15px">Add to Builder</th>
                    <th>Queries</th>
                    <th width="15px">Delete</th>
                </tr>                
            </table>""")
        for query in userQueries:
#             pattern = re.compile("'re.compile(.*)'[,}]")
#             for regex, pattern in query.dictRegex.iteritems():
            for i in range(0, len(query.ListRegex)):
                query.query = query.query.replace(query.ListRegex[i], "re.compile('" + query.ListPattern[i] + "')")
                
            mapQueryInfo[str(query.id)] = QueryInfo(eval(query.query), query.displayedQuery)
            element = html.fragment_fromstring(renderSavedQuery(query.displayedQuery, query.id))            
            queriesTable.append(element)
        dajax.assign('#queriesTable', 'innerHTML', html.tostring(queriesTable))
        
    dajax.assign('#customForm', 'innerHTML', customFormString)
    
    return dajax.json()  

################################################################################
#
# Function Name: saveXMLData(request,xmlContent,formContent)
# Inputs:        request - 
# Outputs:       
# Exceptions:    None
# Description:   
#                
#
################################################################################
@dajaxice_register
def saveCustomData(request,formContent):
    print '>>>>  BEGIN def saveCustomData(request,formContent)'
    dajax = Dajax()

    global xmlString
    global customFormString
    global formString
#     global queryBuilderString
    
#     queryBuilderString = ""

#     xmlString = xmlContent
    formString = formContent

    # modify the form string to only keep the selected elements
    htmlTree = html.fromstring(formContent)
    createCustomTreeForQuery(htmlTree)
    customFormString = html.tostring(htmlTree) + """
    <script>
    $("#customForm").find("li[draggable=true]").draggable({
        helper: "clone",
    });
    </script>
    """

    print '>>>> END def saveCustomData(request,formContent)'
    return dajax.json()  


def createCustomTreeForQuery(htmlTree):
    for ul in htmlTree.findall("./ul"):
        manageUlForQuery(ul)

def manageUlForQuery(ul):
    keepTheBranch = False
    for li in ul.findall("./li"):
        if(manageLiForQuery(li) == True):
            keepTheBranch = True
             
    if(not keepTheBranch):
        li.attrib['style'] = "display:none;"
    return keepTheBranch

            
def manageLiForQuery(li):
    listUl = li.findall("./ul")
    if (len(listUl) != 0):
        keepTheBranch = False
        for ul in listUl:
            if(manageUlForQuery(ul) == True):
                keepTheBranch = True
        if(not keepTheBranch):
            ul.attrib['style'] = "display:none;"
        return keepTheBranch
    else:
        try:
            checkbox = li.find("./nobr/input[@type='checkbox']")
            if(checkbox.attrib['value'] == 'false'):
                li.attrib['style'] = "display:none;"
                return False
            else:
                #remove the checkbox and make the element draggable
                li.attrib['draggable'] = "true"
                li.attrib['style'] = "color:orange;font-weight:bold;cursor:pointer;"
                checkbox.attrib['style'] = "display:none;"
                return True
        except:
            #remove the try catch when custom form will be completly done
            #checkboxes for choices are missing
            return False
  


@dajaxice_register
def downloadResults(request):
    print '>>>>  BEGIN def downloadResults(request)'
    dajax = Dajax()

    global results

    connect('mgi')
    
    if (len(results) > 0):
        xmlResults = []
        for result in results:
            xmlResults.append(str(xmltodict.unparse(result)))
        
        savedResults = queryResults(results=xmlResults).save()
        savedResultsID = str(savedResults.id)
    
        dajax.redirect("/explore/results/download-results?id="+savedResultsID)
    
    print '>>>> END def downloadResults(request)'
    return dajax.json()
# 
# @dajaxice_register
# def saveQueryBuilder(request, queryBuilder):
#     dajax = Dajax()
#     global queryBuilderString
#     
#     queryBuilderString = queryBuilder    
#     
#     return dajax.json()    

@dajaxice_register
def backToQuery(request):
    dajax = Dajax()
    global savedQueryForm
     
    request.session['keepCriterias'] = True
#     dajax.assign("#queryForm", "innerHTML", savedQueryForm)
#     dajax.assign('#queryForm', 'innerHTML', savedQueryForm)
    return dajax.json()
