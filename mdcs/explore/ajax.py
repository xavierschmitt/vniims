################################################################################
#
# File Name: ajax.py
# Application: explore
# Purpose:   
#
# Author: Sharief Youssef
#         sharief.youssef@nist.gov
#
#         Guillaume Sousa Amaral
#         guillaume.sousa@nist.gov
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
from io import BytesIO
from lxml import html
from collections import OrderedDict
from pymongo import Connection
import xmltodict
import requests
import os
import json
import copy

#import xml.etree.ElementTree as etree
import lxml.etree as etree
import xml.dom.minidom as minidom

from mgi.models import Template, QueryResults, SparqlQueryResults, SavedQuery, Jsondata, Instance, XMLSchema

import sparqlPublisher

# Global Variables
debugON = 0

#Class definition
class ElementInfo:    
    def __init__(self, type="", path=""):
        self.type = type
        self.path = path
    
    def __to_json__(self):
        return json.dumps(self, default=lambda o:o.__dict__)
    
class CriteriaInfo:
    def __init__(self, elementInfo=None, queryInfo=None):
        self.elementInfo = elementInfo
        self.queryInfo = queryInfo
    
    def __to_json__(self):
        jsonDict = dict()
        if self.elementInfo == None:
            jsonDict['elementInfo'] = None
        else:
            jsonDict['elementInfo'] = self.elementInfo.__to_json__()
        if self.queryInfo == None:
            jsonDict['queryInfo'] = None
        else:
            jsonDict['queryInfo'] = self.queryInfo.__to_json__()
        return str(jsonDict)
        
class QueryInfo:
    def __init__(self, query="", displayedQuery=""):
        self.query = query
        self.displayedQuery = displayedQuery

    def __to_json__(self):        
        return json.dumps(self, default=lambda o:o.__dict__)
    
class BranchInfo:
    def __init__(self, keepTheBranch, selectedLeave):
        self.keepTheBranch = keepTheBranch
        self.selectedLeave = selectedLeave


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

    # reset global variables
    request.session['formStringExplore'] = ""
    request.session['customFormStringExplore'] = ""
    
    request.session['exploreCurrentTemplate'] = templateFilename
    request.session['exploreCurrentTemplateID'] = templateID
    request.session.modified = True
    print '>>>>' + templateFilename + ' set as current template in session'
    dajax = Dajax()

    templateObject = Template.objects.get(pk=templateID)
    xmlDocData = templateObject.content

    XMLSchema.tree = etree.parse(BytesIO(xmlDocData.encode('utf-8')))
    request.session['xmlDocTreeExplore'] = etree.tostring(XMLSchema.tree)

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
    if 'exploreCurrentTemplateID' in request.session:
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
# @dajaxice_register
# def setCurrentModel(request,modelFilename):
#     print 'BEGIN def setCurrentModel(request)'
#     request.session['exploreCurrentTemplate'] = modelFilename
#     request.session.modified = True
#     print '>>>>' + modelFilename
#     dajax = Dajax()
# 
#     print 'END def setCurrentModel(request)'
#     return dajax.json()


################################################################################
# 
# Function Name: generateFormSubSection(xpath,fullPath)
# Inputs:        xpath -
#                fullPath - 
# Outputs:       JSON data 
# Exceptions:    None
# Description:   
#
################################################################################
def generateFormSubSection(request, xpath, elementName, fullPath, xmlTree):
    print 'BEGIN def generateFormSubSection(xpath, elementName, fullPath)'
    

    global debugON
        
    defaultNamespace = request.session['defaultNamespaceExplore']    
    defaultPrefix = request.session['defaultPrefixExplore']
    nbChoicesID = int(request.session['nbChoicesIDExplore'])
    formString = ""

    if xpath is None:
        print "xpath is none"
        return formString;

    xpathFormated = "./*[@name='"+xpath+"']"
    if debugON: formString += "xpathFormated: " + xpathFormated.format(defaultNamespace)
    e = xmlTree.find(xpathFormated.format(defaultNamespace))

    if e is None:
        return formString

    if e.tag == "{0}complexType".format(defaultNamespace):
        if debugON: formString += "matched complexType" 
        print "matched complexType" + "<br>"
        complexTypeChild = e.find('*')

        if complexTypeChild is None:
            return formString

        fullPath += "." + elementName
        if complexTypeChild.tag == "{0}sequence".format(defaultNamespace):
            formString += "<ul>"
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
                          or sequenceChild.attrib.get('type') == "{0}:float".format(defaultPrefix)
                          or sequenceChild.attrib.get('type') == "{0}:integer".format(defaultPrefix)
                          or sequenceChild.attrib.get('type') == "{0}:anyURI".format(defaultPrefix)):                                                                
                        textCapitalized = sequenceChild.attrib.get('name')   
                        mapTagIDElementInfo = request.session['mapTagIDElementInfoExplore']                  
                        elementID = len(mapTagIDElementInfo.keys())
                        formString += "<li id='" + str(elementID) + "'>" + textCapitalized + " <input type='checkbox'>"                         
                        formString += "</li>"                    
                        elementInfo = ElementInfo(sequenceChild.attrib.get('type'),fullPath[1:] + "." + textCapitalized)
                        mapTagIDElementInfo[elementID] = elementInfo.__to_json__()
                        request.session['mapTagIDElementInfoExplore'] = mapTagIDElementInfo
                    else:                        
                        textCapitalized = sequenceChild.attrib.get('name') 
                        mapTagIDElementInfo = request.session['mapTagIDElementInfoExplore'] 
                        elementID = len(mapTagIDElementInfo.keys())                        
                        isEnum = False
                        # look for enumeration
                        childElement = xmlTree.find("./*[@name='"+sequenceChild.attrib.get('type')+"']".format(defaultNamespace))
                        if (childElement is not None):
                            if(childElement.tag == "{0}simpleType".format(defaultNamespace)):
                                restrictionChild = childElement.find("{0}restriction".format(defaultNamespace))        
                                if restrictionChild is not None:                                    
                                    enumChildren = restrictionChild.findall("{0}enumeration".format(defaultNamespace))
                                    if enumChildren is not None:
                                        formString += "<li id='" + str(elementID) + "'>" + textCapitalized + " <input type='checkbox'>" + "</li>"
                                        elementInfo = ElementInfo("enum",fullPath[1:]+"." + textCapitalized)
                                        mapTagIDElementInfo[elementID] = elementInfo.__to_json__()
                                        request.session['mapTagIDElementInfoExplore'] = mapTagIDElementInfo
                                        listChoices = []
                                        for enumChild in enumChildren:
                                            listChoices.append(enumChild.attrib['value'])
                                        request.session['mapEnumIDChoicesExplore'][elementID] = listChoices
                                        isEnum = True
                        
                        if(isEnum is not True):                            
                            formString += "<li>" + textCapitalized + " "
                            formString += generateFormSubSection(request, sequenceChild.attrib.get('type'), textCapitalized,fullPath, xmlTree)
                            formString += "</li>"                        
                elif sequenceChild.tag == "{0}choice".format(defaultNamespace):
                    chooseID = nbChoicesID
                    chooseIDStr = 'choice' + str(chooseID)
                    nbChoicesID += 1
                    request.session['nbChoicesIDExplore'] = str(nbChoicesID)
                    formString += "<li>Choose <select id='"+ chooseIDStr +"' onchange=\"changeChoice(this);\">"
                    choiceChildren = sequenceChild.findall('*')
#                     selectedChild = choiceChildren[0]
                    for choiceChild in choiceChildren:
                        if choiceChild.tag == "{0}element".format(defaultNamespace):
                            textCapitalized = choiceChild.attrib.get('name')
                            formString += "<option value='" + textCapitalized + "'>" + textCapitalized + "</option></b><br>"
                    formString += "</select></nobr>"                    
                    for (counter, choiceChild) in enumerate(choiceChildren):
                        if choiceChild.tag == "{0}element".format(defaultNamespace):
                            if (choiceChild.attrib.get('type') == "{0}:string".format(defaultPrefix)
                              or choiceChild.attrib.get('type') == "{0}:double".format(defaultPrefix)
                              or choiceChild.attrib.get('type') == "{0}:float".format(defaultPrefix)
                              or choiceChild.attrib.get('type') == "{0}:integer".format(defaultPrefix)
                              or choiceChild.attrib.get('type') == "{0}:anyURI".format(defaultPrefix)):
                                textCapitalized = choiceChild.attrib.get('name')
                                mapTagIDElementInfo = request.session['mapTagIDElementInfoExplore']
                                elementID = len(mapTagIDElementInfo.keys())
                                if (counter > 0):
                                    formString += "<ul id=\"" + chooseIDStr + "-" + str(counter) + "\" style=\"display:none;\"><li id='" + str(elementID) + "'>" + textCapitalized + " <input type='checkbox'>" + "</li></ul>"
                                else:                                      
                                    formString += "<ul id=\"" + chooseIDStr + "-" + str(counter) + "\"><li id='" + str(elementID) + "'>" + textCapitalized + " <input type='checkbox'>" + "</li></ul>"
                                elementInfo = ElementInfo(choiceChild.attrib.get('type'),fullPath[1:]+"." + textCapitalized)
                                mapTagIDElementInfo[elementID] = elementInfo.__to_json__()
                                request.session['mapTagIDElementInfoExplore'] = mapTagIDElementInfo
                            else:
                                textCapitalized = choiceChild.attrib.get('name')
                                if (counter > 0):
                                    formString += "<ul id=\"" + chooseIDStr + "-" + str(counter) + "\" style=\"display:none;\"><li>" + textCapitalized
                                else:
                                    formString += "<ul id=\""  + chooseIDStr + "-" + str(counter) + "\"><li>" + textCapitalized
                                formString += generateFormSubSection(request, choiceChild.attrib.get('type'), textCapitalized, fullPath, xmlTree) + "</ul>"            
            formString += "</li></ul>"
        elif complexTypeChild.tag == "{0}choice".format(defaultNamespace):
            formString += "<ul>"
            if debugON: formString += "complexTypeChild:" + complexTypeChild.tag + "<br>"
            chooseID = nbChoicesID        
            chooseIDStr = 'choice' + str(chooseID)
            nbChoicesID += 1
            request.session['nbChoicesIDExplore'] = str(nbChoicesID)
            formString += "<li>Choose <select id='"+ chooseIDStr +"' onchange=\"changeChoice(this);\">"        
            choiceChildren = complexTypeChild.findall('*')
#             selectedChild = choiceChildren[0]
            for choiceChild in choiceChildren:
                if choiceChild.tag == "{0}element".format(defaultNamespace):
                    textCapitalized = choiceChild.attrib.get('name')
                    formString += "<option value='" + textCapitalized + "'>" + textCapitalized + "</option></b><br>"
            formString += "</select>"
            for (counter, choiceChild) in enumerate(choiceChildren):
                if choiceChild.tag == "{0}element".format(defaultNamespace):
                    if (choiceChild.attrib.get('type') == "{0}:string".format(defaultPrefix)
                      or choiceChild.attrib.get('type') == "{0}:double".format(defaultPrefix)
                      or choiceChild.attrib.get('type') == "{0}:float".format(defaultPrefix)
                      or choiceChild.attrib.get('type') == "{0}:integer".format(defaultPrefix)
                      or choiceChild.attrib.get('type') == "{0}:anyURI".format(defaultPrefix)):
                        textCapitalized = choiceChild.attrib.get('name')
                        mapTagIDElementInfo =  request.session['mapTagIDElementInfoExplore']
                        elementID = len(mapTagIDElementInfo.keys())
                        if (counter > 0):
                            formString += "<ul id=\"" + chooseIDStr + "-" + str(counter) + "\" style=\"display:none;\"><li id='" + str(elementID) + "'>" + textCapitalized + " <input type='checkbox'>" + "</li></ul>"
                        else:                                      
                            formString += "<ul id=\"" + chooseIDStr + "-" + str(counter) + "\"><li id='" + str(elementID) + "'>" + textCapitalized + " <input type='checkbox'>" + "</li></ul>"
                        elementInfo = ElementInfo(choiceChild.attrib.get('type'),fullPath[1:]+"." + textCapitalized)
                        mapTagIDElementInfo[elementID] = elementInfo.__to_json__()
                        request.session['mapTagIDElementInfoExplore'] = mapTagIDElementInfo
                    else:                                                    
                        textCapitalized = choiceChild.attrib.get('name')
                        if (counter > 0):
                            formString += "<ul id=\"" + chooseIDStr + "-" + str(counter) + "\" style=\"display:none;\"><li>" + textCapitalized
                        else:
                            formString += "<ul id=\""  + chooseIDStr + "-" + str(counter) + "\"><li>" + textCapitalized               
                        formString += generateFormSubSection(request, choiceChild.attrib.get('type'), textCapitalized, fullPath, xmlTree) + "</ul>"
            formString += "</li></ul>"
        elif complexTypeChild.tag == "{0}attribute".format(defaultNamespace):
            textCapitalized = complexTypeChild.attrib.get('name')
            formString += "<li>" + textCapitalized + "</li>"
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

    print 'END def generateFormSubSection(xpath, elementName, fullPath)'
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

def generateForm(request):
    print 'BEGIN def generateForm(key)'    
    

    xmlDocTreeStr = request.session['xmlDocTreeExplore']
    xmlDocTree = etree.fromstring(xmlDocTreeStr)
    
    request.session['mapTagIDElementInfoExplore'] = dict()
    request.session['mapEnumIDChoicesExplore'] = dict()
    request.session['nbChoicesIDExplore'] = '0'
    
    formString = ""
    
    defaultNamespace = "http://www.w3.org/2001/XMLSchema"
    for prefix, url in xmlDocTree.nsmap.iteritems():
        if (url == defaultNamespace):            
            request.session['defaultPrefixExplore'] = prefix
            break
    defaultNamespace = "{" + defaultNamespace + "}"
    request.session['defaultNamespaceExplore'] = defaultNamespace
    if debugON: formString += "namespace: " + defaultNamespace + "<br>"
    e = xmlDocTree.findall("./{0}element".format(defaultNamespace))

    if debugON: e = xmlDocTree.findall("{0}complexType/{0}choice/{0}element".format(defaultNamespace))
    if debugON: formString += "list size: " + str(len(e))

#     if len(e) > 1:
    for element in e:
        textCapitalized = element.attrib.get('name')
        formString += "<b>" + textCapitalized + "</b><br>"
        if debugON: formString += "<b>" + element.attrib.get('name').capitalize() + "</b><br>"
        formString += generateFormSubSection(request, element.attrib.get('type'), textCapitalized, "", xmlDocTree)
#         formString += "<p style='color:red'> The schema is not valid ! </p>"
#     else:
#         textCapitalized = e[0].attrib.get('name')[0].capitalize()  + e[0].attrib.get('name')[1:]
#         formString += "<b>" + textCapitalized + "</b><br>"
#         if debugON: formString += "<b>" + e[0].attrib.get('name').capitalize() + "</b><br>"
#         formString += generateFormSubSection(e[0].attrib.get('type'), "")

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

    dajax = Dajax()
    
    if 'formStringExplore' in request.session:
        formString = request.session['formStringExplore']  
    else:
        formString = ''
    
    if 'xmlDocTree' in request.session:
        xmlDocTree = request.session['xmlDocTreeExplore'] 
    else:
        xmlDocTree = ""
    
    templateFilename = request.session['exploreCurrentTemplate']
    templateID = request.session['exploreCurrentTemplateID']
    print '>>>> ' + templateFilename + ' is the current template in session'
    
    if xmlDocTree == "":
        setCurrentTemplate(request,templateFilename, templateID)
        xmlDocTree = request.session['xmlDocTreeExplore']
    if (formString == ""):
        formString = "<form id=\"dataQueryForm\" name=\"xsdForm\">"
        formString += generateForm(request)        
        formString += "</form>"        
    
    dajax.assign('#xsdForm', 'innerHTML', formString)
 
    print 'END def generateXSDTreeForQueryingData(request)'
    return dajax.json()



################################################################################
# 
# Function Name: executeQuery(request, queryForm, queryBuilder, fedOfQueries)
# Inputs:        request - 
#                queryForm - 
#                queryBuilder - 
# Outputs:       
# Exceptions:    None
# Description:   execute a query in mongo db
#
################################################################################
@dajaxice_register
def executeQuery(request, queryForm, queryBuilder, fedOfQueries):
    print 'BEGIN def executeQuery(request, queryForm, queryBuilder, fedOfQueries)'        
    dajax = Dajax()
    
    request.session['savedQueryFormExplore'] = queryForm    
    
    queryFormTree = html.fromstring(queryForm)
    errors = checkQueryForm(request, queryFormTree)
    if(len(errors)== 0):
        instances = getInstances(request, fedOfQueries)
        if (len(instances)==0):
            dajax.script("showErrorInstancesDialog();")
        else:
            htmlTree = html.fromstring(queryForm)
            request.session['queryExplore'] = fieldsToQuery(request, htmlTree)
            json_instances = []
            for instance in instances:
                json_instances.append(instance.to_json()) 
            request.session['instancesExplore'] = json_instances
            dajax.script("resultsCallback();")
    else:
        errorsString = ""
        for error in errors:
            errorsString += "<p>" + error + "</p>"            
        dajax.assign('#listErrors', 'innerHTML', errorsString)
        dajax.script("displayErrors();")

    print 'END def executeQuery(request, queryForm, queryBuilder, fedOfQueries)'
    return dajax.json()

def getInstances(request, fedOfQueries):
    
    instances = []
    fedOfQueriesTree = html.fromstring(fedOfQueries)    
    instancesCheckboxes = fedOfQueriesTree.findall(".//input[@type='checkbox']")
    
    for checkbox in instancesCheckboxes:
        if 'checked' in checkbox.attrib:
            if checkbox.attrib['value'] == "Local":
                if 'HTTPS' in request.META['SERVER_PROTOCOL']:
                    protocol = "https"
                else:
                    protocol = "http"
                instances.append(Instance(name="Local", protocol=protocol, address=request.META['REMOTE_ADDR'], port=request.META['SERVER_PORT'], user="user", password="password"))
            else:
                instances.append(Instance.objects.get(name=checkbox.attrib['value']))
    
    return instances  
    
@dajaxice_register
def getResults(request):
    dajax = Dajax()
    
    instances = request.session['instancesExplore']
    
    dajax.script("""
        getAsyncResults('"""+ str(len(instances)) +"""');
    """)
    
    return dajax.json()

def manageRegexBeforeExe(query):
    for key, value in query.iteritems():
        if key == "$and" or key == "$or":
            for subValue in value:
                manageRegexBeforeExe(subValue)
        elif isinstance(value, unicode):
            if (len(value) > 2 and value[0] == "/" and value[-1] == "/"):
                query[key] = re.compile(value[1:-1])
        elif isinstance(value, dict):
            manageRegexBeforeExe(value)

# ################################################################################
# # 
# # Function Name: getResultsByInstance(request, numInstance)
# # Inputs:        request -  
# # Outputs:       
# # Exceptions:    None
# # Description:   Get results of a query
# #
# ################################################################################
# @dajaxice_register
# def getResultsByInstance(request, numInstance):
#     print 'BEGIN def getResults(request)'
#     dajax = Dajax()
#     
#     query = copy.deepcopy(request.session['queryExplore'])
#     
#     instances = request.session['instancesExplore']
#         
#     resultString = ""
#     results = []    
#     
#     instance = eval(instances[int(numInstance)])
#     sessionName = "resultsExplore" + instance['name']
#     resultString += "<b>From " + instance['name'] + ":</b> <br/>"
#     if instance['name'] == "Local":
#         manageRegexBeforeExe(query)
#         instanceResults = Jsondata.executeQuery(query)
#         if len(instanceResults) > 0:
#             for instanceResult in instanceResults:
#                 results.append(xmltodict.unparse(instanceResult))
# #                 resultString += "<textarea class='xmlResult' readonly='true'>"
#                 resultString += "<div class='xmlResult' readonly='true'>"
#                 xsltPath = os.path.join(settings.SITE_ROOT, 'static/resources/xsl/xml2html.xsl')
#                 xslt = etree.parse(xsltPath)
#                 transform = etree.XSLT(xslt)
#                 dom = etree.fromstring(str(xmltodict.unparse(instanceResult).replace('<?xml version="1.0" encoding="utf-8"?>\n',"")))
#                 newdom = transform(dom)
#                 resultString += str(newdom)
# #                 resultString += str(xmltodict.unparse(instanceResult, pretty=True))
# #                 resultString += "</textarea> <br/>"
#                 resultString += "</div> <br/>"
#             resultString += "<br/>"
#         else:
#             resultString += "<span style='font-style:italic; color:red;'> No Results found... </span><br/><br/>"
#     else:
#         url = instance['protocol'] + "://" + instance['address'] + ":" + str(instance['port']) + "/api/explore/query-by-example"
# #         queryStr = str(query)
# #         queryStr = manageRegexBeforeAPI(query, queryStr)
# #         queryToSend = eval(queryStr)
#         data = {"query":str(query)}
#         r = requests.post(url, data, auth=(instance['user'], instance['password']))   
#         result = r.text
#         instanceResults = json.loads(result,object_pairs_hook=OrderedDict)
#         if len(instanceResults) > 0:
#             for instanceResult in instanceResults:
#                 results.append(xmltodict.unparse(instanceResult['content']))
# #                 resultString += "<textarea class='xmlResult' readonly='true'>"  
# #                 resultString += str(xmltodict.unparse(instanceResult['content'], pretty=True))
# #                 resultString += "</textarea> <br/>"
#                 resultString += "<div class='xmlResult' readonly='true'>"
#                 xsltPath = os.path.join(settings.SITE_ROOT, 'static/resources/xsl/xml2html.xsl')
#                 xslt = etree.parse(xsltPath)
#                 transform = etree.XSLT(xslt)
#                 dom = etree.fromstring(str(xmltodict.unparse(instanceResult['content']).replace('<?xml version="1.0" encoding="utf-8"?>\n',"")))
#                 newdom = transform(dom)
#                 resultString += str(newdom)
#                 resultString += "</div> <br/>"
#             resultString += "<br/>"
#         else:
#             resultString += "<span style='font-style:italic; color:red;'> No Results found... </span><br/><br/>"
#         
#     request.session[sessionName] = results
#     dajax.append("#results", "innerHTML", resultString)
#     
#     print 'END def getResults(request)'
#     return dajax.json()

################################################################################
# 
# Function Name: getResultsByInstance(request, numInstance)
# Inputs:        request -  
# Outputs:       
# Exceptions:    None
# Description:   Get results of a query
#
################################################################################
@dajaxice_register
def getResultsByInstance(request, numInstance):
    print 'BEGIN def getResults(request)'
    dajax = Dajax()   
    
    instances = request.session['instancesExplore']
        
    resultString = ""    
    
    for i in range(int(numInstance)):
        results = []
        instance = eval(instances[int(i)])
        sessionName = "resultsExplore" + instance['name']
        resultString += "<b>From " + instance['name'] + ":</b> <br/>"
        if instance['name'] == "Local":
            query = copy.deepcopy(request.session['queryExplore'])
            manageRegexBeforeExe(query)
            instanceResults = Jsondata.executeQuery(query)
            if len(instanceResults) > 0:
                for instanceResult in instanceResults:
                    results.append(xmltodict.unparse(instanceResult))
    #                 resultString += "<textarea class='xmlResult' readonly='true'>"
                    resultString += "<div class='xmlResult' readonly='true'>"
                    xsltPath = os.path.join(settings.SITE_ROOT, 'static/resources/xsl/xml2html.xsl')
                    xslt = etree.parse(xsltPath)
                    transform = etree.XSLT(xslt)
                    dom = etree.fromstring(str(xmltodict.unparse(instanceResult).replace('<?xml version="1.0" encoding="utf-8"?>\n',"")))
                    newdom = transform(dom)
                    resultString += str(newdom)
    #                 resultString += str(xmltodict.unparse(instanceResult, pretty=True))
    #                 resultString += "</textarea> <br/>"
                    resultString += "</div> <br/>"
                resultString += "<br/>"
            else:
                resultString += "<span style='font-style:italic; color:red;'> No Results found... </span><br/><br/>"
        else:
            url = instance['protocol'] + "://" + instance['address'] + ":" + str(instance['port']) + "/api/explore/query-by-example"
    #         queryStr = str(query)
    #         queryStr = manageRegexBeforeAPI(query, queryStr)
    #         queryToSend = eval(queryStr)
            query = copy.deepcopy(request.session['queryExplore'])
            data = {"query":str(query)}
            r = requests.post(url, data, auth=(instance['user'], instance['password']))   
            result = r.text
            instanceResults = json.loads(result,object_pairs_hook=OrderedDict)
            if len(instanceResults) > 0:
                for instanceResult in instanceResults:
                    results.append(xmltodict.unparse(instanceResult['content']))
    #                 resultString += "<textarea class='xmlResult' readonly='true'>"  
    #                 resultString += str(xmltodict.unparse(instanceResult['content'], pretty=True))
    #                 resultString += "</textarea> <br/>"
                    resultString += "<div class='xmlResult' readonly='true'>"
                    xsltPath = os.path.join(settings.SITE_ROOT, 'static/resources/xsl/xml2html.xsl')
                    xslt = etree.parse(xsltPath)
                    transform = etree.XSLT(xslt)
                    dom = etree.fromstring(str(xmltodict.unparse(instanceResult['content']).replace('<?xml version="1.0" encoding="utf-8"?>\n',"")))
                    newdom = transform(dom)
                    resultString += str(newdom)
                    resultString += "</div> <br/>"
                resultString += "<br/>"
            else:
                resultString += "<span style='font-style:italic; color:red;'> No Results found... </span><br/><br/>"
            
        request.session[sessionName] = results
    dajax.append("#results", "innerHTML", resultString)
    
    print 'END def getResults(request)'
    return dajax.json()

#TODO: can't do a deep copy of a dictionary containing pattern objects (deepcopy bug)
def manageRegexBeforeAPI(query, queryStr):
    for key, value in query.iteritems():
        if key == "$and" or key == "$or":
            for subValue in value:
                queryStr = manageRegexBeforeAPI(subValue, queryStr)
        elif isinstance(value, re._pattern_type):
#             query[key] = "/" + str(value.pattern) + "/"
            queryStr = queryStr.replace(str(value),"'/" + str(value.pattern) + "/'")
        elif isinstance(value, dict):
            queryStr = manageRegexBeforeAPI(value, queryStr)
    return queryStr

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


################################################################################
# 
# Function Name: floatCriteria(path, comparison, value, isNot=False)
# Inputs:        path - 
#                comparison -
#                value -
#                isNot -
# Outputs:       a criteria
# Exceptions:    None
# Description:   Build a criteria for mongo db for the type float
#
################################################################################
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

################################################################################
# 
# Function Name: stringCriteria(path, comparison, value, isNot=False)
# Inputs:        path - 
#                comparison -
#                value -
#                isNot -
# Outputs:       a criteria
# Exceptions:    None
# Description:   Build a criteria for mongo db for the type string
#
################################################################################
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
#             criteria[path]["$not"] = re.compile(value)
            criteria[path]["$not"] = "/" + value + "/"
        else:
#             criteria[path] = re.compile(value)
            criteria[path] = "/" + value + "/"
    
    return criteria

################################################################################
# 
# Function Name: queryToCriteria(query, isNot=False)
# Inputs:        query - 
#                isNot -
# Outputs:       a criteria
# Exceptions:    None
# Description:   Build a criteria for mongo db for a query
#
################################################################################
def queryToCriteria(query, isNot=False):
    if(isNot):
        return invertQuery(query.copy())
    else:
        return query

################################################################################
# 
# Function Name: invertQuery(query)
# Inputs:        query - 
# Outputs:       
# Exceptions:    None
# Description:   Invert each field of the query to build NOT(query)
#
################################################################################
def invertQuery(query):
    for key, value in query.iteritems():
        if key == "$and" or key == "$or":
            for subValue in value:
                invertQuery(subValue)
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

################################################################################
# 
# Function Name: enumCriteria(path, value, isNot=False)
# Inputs:        path -
#                value -
#                isNot -
# Outputs:       criteria
# Exceptions:    None
# Description:   Build a criteria for mongo db for an enumeration
#
################################################################################
def enumCriteria(path, value, isNot=False):
    criteria = dict()
    
    if(isNot):
        criteria[path] = eval('{"$ne":' + repr(value) + '}')
    else:
        criteria[path] = str(value)
            
    return criteria

################################################################################
# 
# Function Name: ANDCriteria(criteria1, criteria2)
# Inputs:        criteria1 -
#                criteria2 -
# Outputs:       criteria
# Exceptions:    None
# Description:   Build a criteria that is the result of criteria1 and criteria2
#
################################################################################
def ANDCriteria(criteria1, criteria2):
#     return criteria1.update(criteria2)
    ANDcriteria = dict()
    ANDcriteria["$and"] = []
    ANDcriteria["$and"].append(criteria1)
    ANDcriteria["$and"].append(criteria2)
    return ANDcriteria

################################################################################
# 
# Function Name: ORCriteria(criteria1, criteria2)
# Inputs:        criteria1 -
#                criteria2 -
# Outputs:       criteria
# Exceptions:    None
# Description:   Build a criteria that is the result of criteria1 or criteria2
#
################################################################################
def ORCriteria(criteria1, criteria2):
    ORcriteria = dict()
    ORcriteria["$or"] = []
    ORcriteria["$or"].append(criteria1)
    ORcriteria["$or"].append(criteria2)
    return ORcriteria

################################################################################
# 
# Function Name: buildCriteria(elemPath, comparison, value, elemType, isNot=False)
# Inputs:        elemPath -
#                comparison -
#                value -
#                elemType - 
#                isNot - 
# Outputs:       criteria
# Exceptions:    None
# Description:   Look at element type and route to the right function to build the criteria
#
################################################################################
def buildCriteria(request, elemPath, comparison, value, elemType, isNot=False):
    defaultPrefix = request.session['defaultPrefixExplore']
    
    if (elemType == '{0}:integer'.format(defaultPrefix)):
        return intCriteria(elemPath, comparison, value, isNot)
    elif (elemType == '{0}:float'.format(defaultPrefix) or elemType == '{0}:double'.format(defaultPrefix)):
        return floatCriteria(elemPath, comparison, value, isNot)
    elif (elemType == '{0}:string'.format(defaultPrefix)):
        return stringCriteria(elemPath, comparison, value, isNot)
    else:
        return stringCriteria(elemPath, comparison, value, isNot)

################################################################################
# 
# Function Name: fieldsToQuery(htmlTree)
# Inputs:        htmlTree -
# Outputs:       query
# Exceptions:    None
# Description:   Take values from the html tree and create a query with them
#
################################################################################
def fieldsToQuery(request, htmlTree):
    
    mapCriterias = request.session['mapCriteriasExplore']
    
    fields = htmlTree.findall("./p")
    
    query = dict()
    for field in fields:        
        boolComp = field[0].value
        if (boolComp == 'NOT'):
            isNot = True
        else:
            isNot = False
            
        criteriaInfo = eval(mapCriterias[field.attrib['id']])
        if criteriaInfo['elementInfo'] is None:
            elementInfo = None
        else:
            elementInfo = eval(criteriaInfo['elementInfo'])
        if criteriaInfo['queryInfo'] is None:
            queryInfo = None
        else:
            queryInfo = eval(criteriaInfo['queryInfo'])
        elemType = elementInfo['type']
        if (elemType == "query"):
            queryValue = queryInfo['query']
            criteria = queryToCriteria(queryValue, isNot)
        elif (elemType == "enum"):
            element = "content." + elementInfo['path']
            value = field[2][0].value            
            criteria = enumCriteria(element, value, isNot)
        else:                
            element = "content." + elementInfo['path']
            comparison = field[2][0].value
            value = field[2][1].value
            criteria = buildCriteria(request, element, comparison, value, elemType , isNot)
        
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

################################################################################
# 
# Function Name: checkQueryForm(htmlTree)
# Inputs:        htmlTree -
# Outputs:       query
# Exceptions:    None
# Description:   Check that values entered by the user match each element type
#
################################################################################
def checkQueryForm(request, htmlTree):
    
    mapCriterias = request.session['mapCriteriasExplore']
    
    if 'defaultPrefixExplore' in request.session:
        defaultPrefix = request.session['defaultPrefixExplore']
    else:
        xmlDocTreeStr = request.session['xmlDocTreeExplore']
        xmlDocTree = etree.fromstring(xmlDocTreeStr)
        
        defaultNamespace = "http://www.w3.org/2001/XMLSchema"
        for prefix, url in xmlDocTree.nsmap.iteritems():
            if (url == defaultNamespace):            
                request.session['defaultPrefixExplore'] = prefix
                defaultPrefix = prefix
                break
        
    
    
    errors = []
    fields = htmlTree.findall("./p")
    if (len(mapCriterias) != len(fields)):
        errors.append("Some fields are empty !")
    else:
        for field in fields:
            criteriaInfo = eval(mapCriterias[field.attrib['id']])
            elementInfo = eval(criteriaInfo['elementInfo']) 
            elemType = elementInfo['type']
            
            if (elemType == "{0}:float".format(defaultPrefix) or elemType == "{0}:double".format(defaultPrefix)):
                value = field[2][1].value
                try:
                    float(value)
                except ValueError:
                    elementPath = elementInfo['path']
                    element = elementPath.split('.')[-1]
                    errors.append(element + " must be a number !")
                        
            elif (elemType == "{0}:integer".format(defaultPrefix)):
                value = field[2][1].value
                try:
                    int(value)
                except ValueError:
                    elementPath = elementInfo['path']
                    element = elementPath.split('.')[-1]
                    errors.append(element + " must be an integer !")
                    
            elif (elemType == "{0}:string".format(defaultPrefix)):
                comparison = field[2][0].value
                value = field[2][1].value
                elementPath = elementInfo['path']
                element = elementPath.split('.')[-1]
                if (comparison == "like"):
                    try:
                        re.compile(value)
                    except Exception, e:
                        errors.append(element + " must be a valid regular expression ! (" + str(e) + ")")
                    
    return errors
                    
################################################################################
# 
# Function Name: addField(request, htmlForm)
# Inputs:        request - 
#                htmlForm -
# Outputs:       
# Exceptions:    None
# Description:   Add an empty field to the query builder
#
################################################################################
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
            <input onclick="showCustomTree('crit""" + str(tagID) + """')" readonly="readonly" type="text" class="elementInput">     
            <span id='ui"""+ str(tagID) +"""'>
            </span>  
            <span class="icon remove" onclick="removeField('crit""" + str(tagID) + """')"></span>
            <span class="icon add" onclick="addField()"></span>
        </p>
    """)
    
    #insert before the 3 buttons (save, clear, execute)
    htmlTree.insert(-3,element)   
    
    dajax.assign("#queryForm", "innerHTML", html.tostring(htmlTree))
    
#     dajax.script("""
#         makeInputsDroppable();
#     """);
    return dajax.json()

################################################################################
# 
# Function Name: removeField(request, queryForm, criteriaID)
# Inputs:        request -
#                htmlForm -
#                criteriaID -
# Outputs:       
# Exceptions:    None
# Description:   Remove a field from the query builder
#
################################################################################
@dajaxice_register
def removeField(request, queryForm, criteriaID):
    dajax = Dajax()    
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
        mapCriterias = request.session['mapCriteriasExplore']
        del mapCriterias[criteriaID]
        request.session['mapCriteriasExplore'] = mapCriterias
    except:
        pass
    
    dajax.assign("#queryForm", "innerHTML", html.tostring(htmlTree))
#     dajax.script("""
#         makeInputsDroppable();
#     """);
    return dajax.json()

################################################################################
# 
# Function Name: renderYESORNOT()
# Inputs:        
# Outputs:       Yes or Not select string
# Exceptions:    None
# Description:   Returns a string that represents an html select with yes or not options
#
################################################################################
def renderYESORNOT():
    return """
    <select>
      <option value=""></option>
      <option value="NOT">NOT</option>
    </select> 
    """

################################################################################
# 
# Function Name: renderANDORNOT()
# Inputs:        
# Outputs:       AND OR NOT select string
# Exceptions:    None
# Description:   Returns a string that represents an html select with AND, OR, NOT options
#
################################################################################
def renderANDORNOT():
    return """
    <select>
      <option value="AND">AND</option>
      <option value="OR">OR</option>
      <option value="NOT">NOT</option>
    </select> 
    """

################################################################################
# 
# Function Name: renderNumericSelect()
# Inputs:        
# Outputs:       numeric select string
# Exceptions:    None
# Description:   Returns a string that represents an html select with numeric comparisons
#
################################################################################
def renderNumericSelect():
    return """
    <select style="width:70px">
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

def renderEnum(request, fromElementID):
    enum = "<select class='selectInput'>"
    listOptions = request.session['mapEnumIDChoicesExplore'][str(fromElementID)]
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
    
    if value == "":
        prettyCriteria += ' &ldquo;  &ldquo;'
    else:
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

def fieldsToPrettyQuery(request, queryFormTree):
    
    mapCriterias = request.session['mapCriteriasExplore']
    
    fields = queryFormTree.findall("./p")
    query = ""
#     criteriaIterator = 0
    for field in fields:        
        boolComp = field[0].value
        if (boolComp == 'NOT'):
            isNot = True
        else:
            isNot = False
                
        criteriaInfo = eval(mapCriterias[field.attrib['id']])
        if criteriaInfo['elementInfo'] is None:
            elementInfo = None
        else:
            elementInfo = eval(criteriaInfo['elementInfo'])
        if criteriaInfo['queryInfo'] is None:
            queryInfo = None
        else:
            queryInfo = eval(criteriaInfo['queryInfo']) 
        elemType = elementInfo['type']
        if (elemType == "query"):
            queryValue = queryInfo['displayedQuery']
#             criteriaIterator += 1
            criteria = queryToPrettyCriteria(queryValue, isNot)
        elif (elemType == "enum"):
            elementPath = elementInfo['path']
            element = elementPath.split('.')[-1]
#             criteriaIterator += 1
            value = field[2][0].value            
            criteria = enumToPrettyCriteria(element, value, isNot)
        else:                 
            elementPath = elementInfo['path']
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
    
    mapQueryInfo = request.session['mapQueryInfoExplore']
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
        errors = checkQueryForm(request, queryFormTree)
        if(len(errors)== 0):
            query = fieldsToQuery(request, queryFormTree)    
            displayedQuery = fieldsToPrettyQuery(request, queryFormTree) 
        
            #save the query in the data base
#             manageRegexBeforeSave(query)
            savedQuery = SavedQuery(str(userID),str(templateID), str(query),displayedQuery)
            savedQuery.save()
            
            #add the query to the table        
#             queriesTree = html.fromstring(queriesList)
#             queriesTable = queriesTree.find("./[@id=queriesTable]")
            queriesTableTree = html.fromstring(queriesTable)
            tr = queriesTableTree.find("./tbody/tr[@id='noqueries']")
            if(tr is not None):
                # removes the row         
                queriesTableTree.find("./tbody").remove(tr) 
    
#             linesInTable = queriesTable.findall("./tbody")
#             if (len(linesInTable) == 1): #th
#                 queryID = 0
#             else:
#                 queryID = int(linesInTable[-1][0].attrib['id'][5:]) + 1
#                 pass
#             mapQueryInfo[queryID] = QueryInfo(query, displayedQuery)
            queryInfo = QueryInfo(query, displayedQuery)
            mapQueryInfo[str(savedQuery.id)] = queryInfo.__to_json__()
            request.session['mapQueryInfoExplore'] = mapQueryInfo
            
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


def manageRegexBeforeSave(query):
#     for key, value in query.iteritems():
#         if isinstance(value, dict):
#             manageRegexBeforeSave(value)
#         else:
#             if isinstance(value, re._pattern_type):
#                 query[key] = "re.compile(" + value.pattern + ")"
    for key, value in query.iteritems():
        if key == "$and" or key == "$or":
            for subValue in value:
                manageRegexBeforeSave(subValue)
        elif isinstance(value, re._pattern_type):
            query[key] = "/" + str(value.pattern) + "/"
        elif isinstance(value, dict):
            manageRegexBeforeSave(value)
#                 DictRegex[str(value).replace(".", "")] = value.pattern

@dajaxice_register
def deleteQuery(request, queriesTable, savedQueryID):
    dajax = Dajax()
    
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
    
    SavedQuery(id=savedQueryID[5:]).delete()
    
    mapQueryInfo = request.session['mapQueryInfoExplore']
    del mapQueryInfo[savedQueryID[5:]]
    request.session['mapQueryInfoExplore'] = mapQueryInfo
    
    if '_auth_user_id' in request.session and 'exploreCurrentTemplateID' in request.session:
        userID = request.session['_auth_user_id']
        templateID = request.session['exploreCurrentTemplateID']
        userQueries = SavedQuery.objects(user=str(userID),template=str(templateID))        
        if(len(userQueries) == 0):
            queriesTableTree = html.fragment_fromstring(
            """<table>
                <tr>                    
                    <th width="15px">Add to Builder</th>
                    <th>Queries</th>
                    <th width="15px">Delete</th>
                </tr>                
            </table>""")
            element = html.fragment_fromstring(renderNoQueries())
            queriesTableTree.append(element)
    dajax.assign("#queriesTable", "innerHTML", html.tostring(queriesTableTree))
#     dajax.script(""" 
#         makeInputsDroppable();    
#     """);
    return dajax.json()
    
    
def renderSavedQuery(query, queryID):
    return """
        <tr id=query"""+ str(queryID) +""">
            <td><span class="icon upload" onclick="addSavedQueryToForm('query"""+ str(queryID) +"""')"></span></td>
            <td>""" + query +  """</td>
            <td><span class="icon invalid" onclick="deleteQuery('query"""+ str(queryID) +"""')"></span></td>
        </tr>
    """

# def checkTypes(queryFormTree, errors):
#     areTypesOK = True
#       
#     for criteria in queryFormTree.findall("./p"):
#         type = mapCriterias[criteria.attrib['id']].elementInfo.type
#         if (type == "integer"):
#             try:
#                 int(criteria[2][1].value)
#             except:
#                 errors.append(criteria[1].value + " must be of type : " + type)
#         elif (type == "string"):
#             pass
#         elif (type == "double"):
#             pass
#         elif (type == "query"):
#             pass
#         
#     return areTypesOK

@dajaxice_register
def updateUserInputs(request, htmlForm, fromElementID, criteriaID):   
    dajax = Dajax()
    
    mapTagIDElementInfo = request.session['mapTagIDElementInfoExplore']
    mapCriterias = request.session['mapCriteriasExplore']
    defaultPrefix = request.session['defaultPrefixExplore']
    
    toCriteriaID = "crit" + str(criteriaID)
    
    criteriaInfo = CriteriaInfo()
    criteriaInfo.elementInfo = ElementInfo(path=eval(mapTagIDElementInfo[str(fromElementID)])['path'], type=eval(mapTagIDElementInfo[str(fromElementID)])['type'])
    mapCriterias[toCriteriaID] = criteriaInfo.__to_json__()
    request.session['mapCriteriasExplore'] = mapCriterias
    
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
    
    if (criteriaInfo.elementInfo.type == "{0}:integer".format(defaultPrefix) 
        or criteriaInfo.elementInfo.type == "{0}:double".format(defaultPrefix)
        or criteriaInfo.elementInfo.type == "{0}:float".format(defaultPrefix)):
        form = html.fragment_fromstring(renderNumericSelect())
        inputs = html.fragment_fromstring(renderValueInput()) 
        userInputs.append(form)
        userInputs.append(inputs) 
    elif (criteriaInfo.elementInfo.type == "enum"):
        form = html.fragment_fromstring(renderEnum(request, fromElementID))
        userInputs.append(form)
    else:
        form = html.fragment_fromstring(renderStringSelect())
        inputs = html.fragment_fromstring(renderValueInput())
        userInputs.append(form)
        userInputs.append(inputs)
        

#     userInputs.getparent()[1].attrib['class'] = "elementInput ui-droppable"
    
    dajax.assign("#queryForm", "innerHTML", html.tostring(htmlTree))
#     dajax.script("""
#         makeInputsDroppable();    
#     """);
    return dajax.json()
    
    
@dajaxice_register
def addSavedQueryToForm(request, queryForm, savedQueryID):
    dajax = Dajax()
    
    mapQueryInfo = request.session['mapQueryInfoExplore']
    queryTree = html.fromstring(queryForm)
    
    fields = queryTree.findall("./p")
    fields[-1].remove(fields[-1].find("./span[@class='icon add']"))      
    if (len(fields) == 1):
        criteriaID = fields[0].attrib['id']
        minusButton = html.fragment_fromstring("""<span class="icon remove" onclick="removeField('""" + str(criteriaID) +"""')"></span>""")
        fields[0].append(minusButton)
        
    lastID = fields[-1].attrib['id'][4:]
    queryInfo = eval(mapQueryInfo[savedQueryID[5:]])
    query = queryInfo['displayedQuery']
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
            <input onclick="showCustomTree('crit""" + str(tagID) + """')" readonly="readonly" type="text" class="queryInput" value=" """+ str(query) +""" ">     
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
                <input onclick="showCustomTree('crit""" + str(tagID) + """')" readonly="readonly" type="text" class="queryInput" value=" """+ str(query) +""" ">     
                <span id="ui"""+ str(tagID) +"""">
                </span>  
                <span class="icon remove" onclick="removeField('crit"""+ str(tagID) +"""')"></span>
                <span class="icon add" onclick="addField()"> </span>
            </p>
        """)  
#             break
    
    #insert before the 3 buttons (save, clear, execute)
    queryTree.insert(-3,element)
    
    mapCriterias = request.session['mapCriteriasExplore']
    criteriaInfo = CriteriaInfo()
    criteriaInfo.queryInfo = QueryInfo(query=eval(mapQueryInfo[savedQueryID[5:]])['query'], displayedQuery=eval(mapQueryInfo[savedQueryID[5:]])['displayedQuery'])
    criteriaInfo.elementInfo = ElementInfo("query")
    mapCriterias['crit'+ str(tagID)] = criteriaInfo.__to_json__() 
    request.session['mapCriteriasExplore'] = mapCriterias
    dajax.assign("#queryForm", "innerHTML", html.tostring(queryTree))
#     dajax.script("""    
#         makeInputsDroppable();    
#     """);
    return dajax.json()
    

def renderInitialForm():
    return """
    <p id="crit0">
        <select>
          <option value=""></option>
          <option value="NOT">NOT</option>
        </select> 
        <input onclick="showCustomTree('crit0')" readonly="readonly" type="text" class="elementInput"/>
        <span id="ui0">
        </span>                        
        <span class="icon add" onclick="addField()"></span>                                
    </p>
    """

@dajaxice_register
def clearCriterias(request, queryForm):
    """ Reset Saved Criterias """
    dajax = Dajax()
    
    # Load the criterias tree     
    queryTree = html.fromstring(queryForm)
    
    fields = queryTree.findall("./p")
    for field in fields:
        queryTree.remove(field)
    
    initialForm = html.fragment_fromstring(renderInitialForm())
    queryTree.insert(0,initialForm)  
    
    request.session['mapCriteriasExplore'] = dict()
      
    dajax.assign("#queryForm", "innerHTML", html.tostring(queryTree))
#     dajax.script("""   
#         makeInputsDroppable();    
#     """);
    return dajax.json()
    
@dajaxice_register
def clearQueries(request):
    """ Reset Saved Queries """
    dajax = Dajax()
    
    mapQueryInfo = request.session['mapQueryInfoExplore']
    
#     queriesTableTree = html.fromstring(queriesTable)
#         
#     # finds all lines in the table exept the first one : headers
#     for tr in queriesTableTree.findall('./tbody/tr')[1:]:
#         # removes existing rows         
#         queriesTableTree.find("./tbody").remove(tr)    
    for queryID in mapQueryInfo.keys():
        SavedQuery(id=queryID).delete()
            
    request.session['mapQueryInfoExplore'] = dict()
    
    if '_auth_user_id' in request.session and 'exploreCurrentTemplateID' in request.session:
        userID = request.session['_auth_user_id']
        templateID = request.session['exploreCurrentTemplateID']
        userQueries = SavedQuery.objects(user=str(userID),template=str(templateID))
        queriesTableTree = html.fragment_fromstring(
            """<table>
                <tr>                    
                    <th width="15px">Add to Builder</th>
                    <th>Queries</th>
                    <th width="15px">Delete</th>
                </tr>                
            </table>""")
        if(len(userQueries) == 0):
            element = html.fragment_fromstring(renderNoQueries())
            queriesTableTree.append(element)
        
        
    dajax.assign("#queriesTable", "innerHTML", html.tostring(queriesTableTree))
    # render table again     
#     dajax.script("""  
#         makeInputsDroppable();    
#     """);
    return dajax.json()

def renderNoQueries():
    return "<tr id='noqueries'><td colspan='3' style='color:red;'>No Saved Queries for now.</td></tr>"

def manageRegexFromDB(query):
    for key, value in query.iteritems():
        if key == "$and" or key == "$or":
            for subValue in value:
                manageRegexFromDB(subValue)
        elif isinstance(value, str):
            if (len(value) > 2 and value[0] == "/" and value[-1] == "/"):
                query[key] = re.compile(value[1:-1])
        elif isinstance(value, dict):
            manageRegexFromDB(value)

@dajaxice_register
def getCustomForm(request):
    dajax = Dajax()
    
#     if 'currentExploreTab' in request.session and request.session['currentExploreTab'] == "tab-1":
    mapQueryInfo = dict()
    
    if 'savedQueryFormExplore' in request.session:
        savedQueryForm = request.session['savedQueryFormExplore']
    else:
        savedQueryForm = ""
    customFormString = request.session['customFormStringExplore']
    #delete criterias if user comes from another page than results
    if 'keepCriterias' in request.session:
        del request.session['keepCriterias']
        if savedQueryForm != "" :
            dajax.assign("#queryForm", "innerHTML", savedQueryForm)
            request.session['savedQueryFormExplore'] = ""
    else:
        request.session['mapCriteriasExplore'] = dict()
    
    #Get saved queries of an user
    request.session['mapQueryInfoExplore'] = dict()
    if '_auth_user_id' in request.session and 'exploreCurrentTemplateID' in request.session:
        userID = request.session['_auth_user_id']
        templateID = request.session['exploreCurrentTemplateID']
        userQueries = SavedQuery.objects(user=str(userID),template=str(templateID))
        queriesTable = html.fragment_fromstring(
            """<table>
                <tr>                    
                    <th width="15px">Add to Builder</th>
                    <th>Queries</th>
                    <th width="15px">Delete</th>
                </tr>                
            </table>""")
        if(len(userQueries) == 0):
            element = html.fragment_fromstring(renderNoQueries())
            queriesTable.append(element)
        else:
            for savedQuery in userQueries:
                query = eval(savedQuery.query)
#                 manageRegexFromDB(query)     
                queryInfo = QueryInfo(query, savedQuery.displayedQuery)
                mapQueryInfo[str(savedQuery.id)] = queryInfo.__to_json__()
                request.session['mapQueryInfoExplore'] = mapQueryInfo
                element = html.fragment_fromstring(renderSavedQuery(savedQuery.displayedQuery, savedQuery.id))            
                queriesTable.append(element)
        dajax.assign('#queriesTable', 'innerHTML', html.tostring(queriesTable))
        
    if (customFormString != ""):
        if 'currentExploreTab' in request.session and request.session['currentExploreTab'] == "tab-1":
            dajax.assign('#customForm', 'innerHTML', customFormString)
            dajax.assign('#sparqlCustomForm', 'innerHTML', "")
        elif 'currentExploreTab' in request.session and request.session['currentExploreTab'] == "tab-2":
            dajax.assign('#sparqlCustomForm', 'innerHTML', customFormString)
            dajax.assign('#customForm', 'innerHTML', "")
    else:
        customFormErrorMsg = "<p style='color:red;'>You should customize the template first. <a href='/explore/customize-template' style='color:red;font-weight:bold;'>Go back to Step 2 </a> and select the elements that you want to use in your queries.</p>"
        dajax.assign('#customForm', 'innerHTML', customFormErrorMsg)
        dajax.assign('#sparqlCustomForm', 'innerHTML', customFormErrorMsg)
    
#     elif 'currentExploreTab' in request.session and request.session['currentExploreTab'] == "tab-2":
    
    if 'sparqlQueryExplore' in request.session and request.session['sparqlQueryExplore'] != "":
        sparqlQuery = request.session['sparqlQueryExplore']
    else:
        sparqlQuery = ""
        
    if sparqlQuery != "" :        
        dajax.assign('#SPARQLqueryBuilder .SPARQLTextArea', 'innerHTML', sparqlQuery)
        request.session['sparqlQueryExplore'] = ""
    
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

    request.session['formStringExplore']  = formContent

    # modify the form string to only keep the selected elements
    htmlTree = html.fromstring(formContent)
    createCustomTreeForQuery(request, htmlTree)
    anyChecked = request.session['anyCheckedExplore']
    if (anyChecked):
        request.session['customFormStringExplore'] = html.tostring(htmlTree)
    else:
        request.session['customFormStringExplore'] = ""
    
    request.session['anyCheckedExplore'] = False 
#     + """
#     <script>
#     $("#customForm").find("li[draggable=true]").draggable({
#         helper: "clone",
#     });
#     
#     $( "#queryForm input[droppable=true]" ).droppable({
#         hoverClass: "ui-state-hover",
#         drop: function( event, ui ) {
#             $(this).val(ui.draggable.text());
#             updateUserInputs(ui.draggable.attr('id'),$(this).parent().attr('id')); 
#         }
#     });
#     </script>
#     """

    print '>>>> END def saveCustomData(request,formContent)'
    return dajax.json()  

def createCustomTreeForQuery(request, htmlTree):
    request.session['anyCheckedExplore'] = False
    for li in htmlTree.findall("./ul/li"):
        manageLiForQuery(request, li)

def manageUlForQuery(request, ul):
    branchInfo = BranchInfo(keepTheBranch = False, selectedLeave = None)
#     hasOnlyLeaves = True
    selectedLeaves = []
    for li in ul.findall("./li"):
        liBranchInfo = manageLiForQuery(request, li)
        if(liBranchInfo.keepTheBranch == True):
            branchInfo.keepTheBranch = True
#         if(liBranchInfo.branchType == "branch"):
#             hasOnlyLeaves = False
        if (liBranchInfo.selectedLeave is not None):
            selectedLeaves.append(liBranchInfo.selectedLeave)
             
    if(not branchInfo.keepTheBranch):
        ul.attrib['style'] = "display:none;"
#     elif(hasOnlyLeaves and nbSelectedLeaves >1): # starting at 2 because 1 is the regular case
    elif(len(selectedLeaves) >1):
        parent = ul.getparent()
        parent.attrib['style'] = "color:purple;font-weight:bold;cursor:pointer;"
        leavesID = ""
        for leave in selectedLeaves[:-1]:
            leavesID += leave + " "
        leavesID += selectedLeaves[-1]
#         parent.attrib['onclick'] = "selectParent('"+ leavesID +"')"
        parent.insert(0, html.fragment_fromstring("""<span onclick="selectParent('"""+ leavesID +"""')">"""+ parent.text +"""</span>"""))
        parent.text = ""
    return branchInfo

            
def manageLiForQuery(request, li):
    listUl = li.findall("./ul")
    branchInfo = BranchInfo(keepTheBranch = False, selectedLeave = None)
    if (len(listUl) != 0):
        for ul in listUl:
            ulBranchInfo = manageUlForQuery(request, ul)
            if(ulBranchInfo.keepTheBranch == True):
                branchInfo.keepTheBranch = True
        if(not branchInfo.keepTheBranch):
            li.attrib['style'] = "display:none;"
        return branchInfo
    else:
        try:
            checkbox = li.find("./input[@type='checkbox']")
            if(checkbox.attrib['value'] == 'false'):
                li.attrib['style'] = "display:none;"
                return branchInfo
            else:
                request.session['anyCheckedExplore'] = True
                # remove the checkbox and make the element clickable
                li.attrib['style'] = "color:orange;font-weight:bold;cursor:pointer;"
                li.attrib['onclick'] = "selectElement("+ li.attrib['id'] +")"
                checkbox.attrib['style'] = "display:none;"   
                # tells to keep this branch until this leave
                branchInfo.keepTheBranch = True
                branchInfo.selectedLeave = li.attrib['id']          
                return branchInfo
        except:
            return branchInfo
  


@dajaxice_register
def downloadResults(request):
    print '>>>>  BEGIN def downloadResults(request)'
    dajax = Dajax()

    instances = request.session['instancesExplore']
    
    xmlResults = []
    for instance in instances:
        sessionName = "resultsExplore" + eval(instance)['name']
        results = request.session[sessionName]
    
        if (len(results) > 0):            
            for result in results:
                xmlResults.append(result)
            
    savedResults = QueryResults(results=xmlResults).save()
    savedResultsID = str(savedResults.id)
        
    dajax.redirect("/explore/results/download-results?id="+savedResultsID)
    
    print '>>>> END def downloadResults(request)'
    return dajax.json()
  

@dajaxice_register
def backToQuery(request):
    dajax = Dajax()
     
    request.session['keepCriterias'] = True

    return dajax.json()


@dajaxice_register
def redirectExplore(request):
    dajax = Dajax()
    
    request.session['currentExploreTab'] = "tab-2"
    dajax.redirect("/explore")
    
    return dajax.json()

@dajaxice_register
def redirectExploreTabs(request):
    dajax = Dajax()
       
    if 'currentExploreTab' in request.session and request.session['currentExploreTab'] == "tab-2":
        dajax.script("redirectSPARQLTab();")
    else:
        dajax.script("switchTabRefresh();")
    
    return dajax.json()

@dajaxice_register
def switchExploreTab(request,tab):
    dajax = Dajax()
    
    request.session["currentExploreTab"] = tab
    
    if 'customFormStringExplore' in request.session:   
        customFormString = request.session['customFormStringExplore']
    else:
        customFormString = ""
    
    if (customFormString != ""):
        if 'currentExploreTab' in request.session and request.session['currentExploreTab'] == "tab-1":
            dajax.assign('#customForm', 'innerHTML', customFormString)
            dajax.assign('#sparqlCustomForm', 'innerHTML', "")
        elif 'currentExploreTab' in request.session and request.session['currentExploreTab'] == "tab-2":
            dajax.assign('#sparqlCustomForm', 'innerHTML', customFormString)
            dajax.assign('#customForm', 'innerHTML', "")
    
    return dajax.json()


@dajaxice_register
def setCurrentCriteria(request, currentCriteriaID):
    dajax = Dajax()
    
    request.session['criteriaIDExplore'] = currentCriteriaID
    
    return dajax.json()

@dajaxice_register
def selectElement(request, elementID, elementName): 
    dajax = Dajax()
    
    if 'currentExploreTab' in request.session and request.session['currentExploreTab'] == "tab-1":
        criteriaID = request.session['criteriaIDExplore']    
        dajax.script("""
            $($("#"""+ criteriaID +"""").children()[1]).val('"""+ elementName +"""');
            $($("#"""+ criteriaID +"""").children()[1]).attr("class","elementInput");
            updateUserInputs("""+ str(elementID) +""", """+ str(criteriaID[4:]) +"""); 
            $("#dialog-customTree").dialog("close");    
        """)
        
        request.session['criteriaIDExplore'] = ""
    elif 'currentExploreTab' in request.session and request.session['currentExploreTab'] == "tab-2":
        mapTagIDElementInfo = request.session['mapTagIDElementInfoExplore']
        elementPath = eval(mapTagIDElementInfo[str(elementID)])['path']
        elementPath = elementPath.replace(".","/tpl:")
        elementPath = "tpl:" + elementPath
        
        queryExample = """SELECT ?""" + elementName + """Value
WHERE {
?s """ + elementPath + """ ?o .
?o rdf:value ?""" + elementName + """Value .
}
"""
        dajax.script("""
            $("#sparqlElementPath").val('"""+ elementPath + """');
        """)
        dajax.assign("#sparqlExample", "innerHTML", queryExample)
    return dajax.json()

@dajaxice_register
def executeSPARQLQuery(request, queryStr, sparqlFormatIndex, fedOfQueries):
    print 'BEGIN def executeSPARQLQuery(request, queryStr, sparqlFormatIndex)'        
    dajax = Dajax()
    
    instances = getInstances(request, fedOfQueries)
    if (len(instances)==0):
        dajax.script("showErrorInstancesDialog();")
    else:
        json_instances = []
        for instance in instances:
            json_instances.append(instance.to_json()) 
        request.session['instancesExplore'] = json_instances
        request.session['sparqlQueryExplore'] = queryStr
        request.session['sparqlFormatExplore'] = str(sparqlFormatIndex)
        dajax.script("sparqlResultsCallback();")

    print 'END def executeSPARQLQuery(request, queryStr, sparqlFormatIndex)'
    return dajax.json()

@dajaxice_register
def getSparqlResults(request):
    dajax = Dajax()
    
    instances = request.session['instancesExplore']    
    request.session['sparqlResultsExplore'] = ""
    
    dajax.script("""
        getAsyncSparqlResults('"""+ str(len(instances)) +"""');
    """)
    
    return dajax.json()

# from threading import Thread, Lock
# mutex = Lock()

# @dajaxice_register
# def getSparqlResultsByInstance(request, numInstance):
#     dajax = Dajax()
#     global mutex
#     mutex.acquire()
#     try:      
#         instances = request.session['instancesExplore']
#         sparqlQuery = request.session['sparqlQueryExplore']    
#         sparqlFormat = request.session['sparqlFormatExplore']
#         
#         resultString = ""
#         instance = eval(instances[int(numInstance)])
#         sessionName = "sparqlResultsExplore" + instance['name']
#         print sessionName + "lock"
#         resultString += "<b>From " + instance['name'] + ":</b> <br/>"
#         if instance['name'] == "Local":
#             instanceResults = sparqlPublisher.sendSPARQL(sparqlFormat + sparqlQuery)
#             request.session[sessionName] = instanceResults
#             displayedSparqlResults = instanceResults.replace("<", "&#60;")
#             displayedSparqlResults = displayedSparqlResults.replace(">", "&#62;")
#             resultString += "<pre class='sparqlResult' readonly='true'>"
#             resultString += displayedSparqlResults
#             resultString += "</pre>"
#             resultString += "<br/>"
#         else:
#             url = instance['protocol'] + "://" + instance['address'] + ":" + str(instance['port']) + "/api/explore/sparql-query"
#             resFormat = ""
#             if (sparqlFormat == "0"):
#                 resFormat = "TEXT"
#             elif (sparqlFormat == "1"):
#                 resFormat = "XML"
#             elif (sparqlFormat == "2"):
#                 resFormat = "CSV"
#             elif (sparqlFormat == "3"):
#                 resFormat = "TSV"
#             elif (sparqlFormat == "4"):
#                 resFormat = "JSON"
#             data = {"query": sparqlQuery, "format": resFormat}
#             try:
#                 r = requests.post(url, data, auth=(instance['user'], instance['password']))
#                 instanceResultsDict = eval(r.text)
#                 instanceResults = instanceResultsDict['content']  
#                 request.session[sessionName] = instanceResults
#                 displayedSparqlResults = instanceResults.replace("<", "&#60;")
#                 displayedSparqlResults = displayedSparqlResults.replace(">", "&#62;")        
#                 resultString += "<pre class='sparqlResult' readonly='true'>"
#                 resultString += displayedSparqlResults
#                 resultString += "</pre>"
#                 resultString += "<br/>"
#             except:            
#                 request.session[sessionName] = ""
#                 resultString += "<p style='color:red;'>Unable to contact the remote instance.</p>"
#     
#         dajax.append("#results", "innerHTML", resultString)
#         
#         request.session.modified = True
#         request.session.save()
#     except Exception, e:
#         print "error in :" + sessionName
#         print e.message
#         mutex.release()
#         return dajax.json()
#     mutex.release()
#     print sessionName + "release"
#     return dajax.json()

@dajaxice_register
def getSparqlResultsByInstance(request, numInstance):
    dajax = Dajax()
    
    resultString = ""
    
    for i in range(int(numInstance)):
        instances = request.session['instancesExplore']
        sparqlQuery = request.session['sparqlQueryExplore']    
        sparqlFormat = request.session['sparqlFormatExplore']
                
        instance = eval(instances[int(i)])
        sessionName = "sparqlResultsExplore" + instance['name']
        resultString += "<b>From " + instance['name'] + ":</b> <br/>"
        if instance['name'] == "Local":
            instanceResults = sparqlPublisher.sendSPARQL(sparqlFormat + sparqlQuery)
            request.session[sessionName] = instanceResults
            displayedSparqlResults = instanceResults.replace("<", "&#60;")
            displayedSparqlResults = displayedSparqlResults.replace(">", "&#62;")
            resultString += "<pre class='sparqlResult' readonly='true'>"
            resultString += displayedSparqlResults
            resultString += "</pre>"
            resultString += "<br/>"
        else:
            url = instance['protocol'] + "://" + instance['address'] + ":" + str(instance['port']) + "/api/explore/sparql-query"
            resFormat = ""
            if (sparqlFormat == "0"):
                resFormat = "TEXT"
            elif (sparqlFormat == "1"):
                resFormat = "XML"
            elif (sparqlFormat == "2"):
                resFormat = "CSV"
            elif (sparqlFormat == "3"):
                resFormat = "TSV"
            elif (sparqlFormat == "4"):
                resFormat = "JSON"
            data = {"query": sparqlQuery, "format": resFormat}
            try:
                r = requests.post(url, data, auth=(instance['user'], instance['password']))
                instanceResultsDict = eval(r.text)
                instanceResults = instanceResultsDict['content']  
                request.session[sessionName] = instanceResults
                displayedSparqlResults = instanceResults.replace("<", "&#60;")
                displayedSparqlResults = displayedSparqlResults.replace(">", "&#62;")        
                resultString += "<pre class='sparqlResult' readonly='true'>"
                resultString += displayedSparqlResults
                resultString += "</pre>"
                resultString += "<br/>"
            except:
                request.session[sessionName] = ""
                resultString += "<p style='color:red;'>Unable to contact the remote instance.</p>"
    
    dajax.append("#results", "innerHTML", resultString)
       
    return dajax.json()
    
@dajaxice_register
def downloadSparqlResults(request):
    print '>>>>  BEGIN def downloadSparqlResults(request)'
    dajax = Dajax()

    instances = request.session['instancesExplore']
    sparqlResults = ""
    for instance in instances:
        sessionName = "sparqlResultsExplore" + eval(instance)['name']
        results = request.session[sessionName]
    
        if (len(results) > 0):            
            sparqlResults += results

        
    savedResults = SparqlQueryResults(results=sparqlResults).save()
    savedResultsID = str(savedResults.id)

    dajax.redirect("/explore/results/download-sparqlresults?id="+savedResultsID)
    
    print '>>>> END def downloadSparqlResults(request)'
    return dajax.json()

@dajaxice_register
def prepareSubElementQuery(request, leavesID):
    print '>>>>  BEGIN def prepareSubElementQuery(request, leavesID)'
    dajax = Dajax()
    
    mapTagIDElementInfo =  request.session['mapTagIDElementInfoExplore']
    
    defaultPrefix = request.session['defaultPrefixExplore']
    
    listLeavesId = leavesID.split(" ")
    firstElementPath = eval(mapTagIDElementInfo[str(listLeavesId[0])])['path']
    parentPath = ".".join(firstElementPath.split(".")[:-1])
    parentName = parentPath.split(".")[-1]
    
    subElementQueryBuilderStr = "<p><b>" +parentName+ "</b></p>"
    subElementQueryBuilderStr += "<ul>"
    for leaveID in listLeavesId:
        elementInfo = ElementInfo(path=eval(mapTagIDElementInfo[str(leaveID)])['path'], type=eval(mapTagIDElementInfo[str(leaveID)])['type'])
        elementName = elementInfo.path.split(".")[-1]
        subElementQueryBuilderStr += "<li><input type='checkbox' style='margin-right:4px;margin-left:2px;' checked/>"
        subElementQueryBuilderStr += renderYESORNOT()
        subElementQueryBuilderStr += elementName + ": "
        if (elementInfo.type == "{0}:integer".format(defaultPrefix) 
        or elementInfo.type == "{0}:double".format(defaultPrefix)
        or elementInfo.type == "{0}:float".format(defaultPrefix)):
            subElementQueryBuilderStr += renderNumericSelect()
            subElementQueryBuilderStr += renderValueInput()
        elif (elementInfo.type == "enum"):
            subElementQueryBuilderStr += renderEnum(request, leaveID)
        else:
            subElementQueryBuilderStr += renderStringSelect()
            subElementQueryBuilderStr += renderValueInput()
        subElementQueryBuilderStr += "</li><br/>"
    subElementQueryBuilderStr += "</ul>"
    
    dajax.assign("#subElementQueryBuilder", "innerHTML", subElementQueryBuilderStr)    
    
    print '>>>>  END def prepareSubElementQuery(request, leavesID)'
    return dajax.json()

@dajaxice_register
def insertSubElementQuery(request, leavesID, form):
    print '>>>>  BEGIN def insertSubElementQuery(request, leavesID, form)'
    dajax = Dajax()
    
    mapTagIDElementInfo = request.session['mapTagIDElementInfoExplore'] 
    
    mapCriterias = request.session['mapCriteriasExplore']
    criteriaID = request.session['criteriaIDExplore']
    
    htmlTree = html.fromstring(form)
    listLi = htmlTree.findall("ul/li")
    listLeavesId = leavesID.split(" ")
    
    i = 0
    nbSelected = 0
    errors = []
    for li in listLi:
        if (li[0].attrib['value'] == 'true'):
            nbSelected += 1            
            elementInfo = ElementInfo(path=eval(mapTagIDElementInfo[str(listLeavesId[i])])['path'], type=eval(mapTagIDElementInfo[str(listLeavesId[i])])['type'])
            elementName = elementInfo.path.split(".")[-1]
            elementType = elementInfo.type
            error = checkSubElementField(request, li, elementName, elementType)
            if (error != ""):
                errors.append(error)
        i += 1
    
    if (nbSelected < 2):
        errors = ["Please select at least two elements."]
    
    if(len(errors) == 0):
        query = subElementfieldsToQuery(request, listLi, listLeavesId)
        prettyQuery = subElementfieldsToPrettyQuery(request, listLi, listLeavesId)
        criteriaInfo = CriteriaInfo()
        criteriaInfo.queryInfo = QueryInfo(query, prettyQuery)
        criteriaInfo.elementInfo = ElementInfo("query")
        mapCriterias[criteriaID] = criteriaInfo.__to_json__()
        request.session['mapCriteriasExplore'] = mapCriterias
        uiID = "ui" + criteriaID[4:]
        dajax.script("""
            // insert the pretty query in the query builder
            $($("#"""+ criteriaID +"""").children()[1]).attr("value",'"""+ prettyQuery +"""');
            var field = $("#"""+ criteriaID +"""").children()[1]
            // replace the pretty by an encoded version
            $(field).attr("value",$(field).html($(field).attr("value")).text())
            // set the class to query
            $($("#"""+ criteriaID +"""").children()[1]).attr("class","queryInput");
            // remove all other existing inputs
            $("#"""+uiID+"""").children().remove();
            // close the dialog
            $("#dialog-subElementQuery").dialog("close");    
        """)        
    else:
        errorsString = ""
        for error in errors:
            errorsString += "<p>" + error + "</p>"            
        dajax.assign('#listErrors', 'innerHTML', errorsString)
        dajax.script("displayErrors();")
            
    
    print '>>>>  END def insertSubElementQuery(request, leavesID, form)'
    return dajax.json()

def checkSubElementField(request, liElement, elementName, elementType):   
    error = ""
    defaultPrefix = request.session['defaultPrefixExplore']
    
    if (elementType == "{0}:float".format(defaultPrefix) or elementType == "{0}:double".format(defaultPrefix)):
        value = liElement[3].value
        try:
            float(value)
        except ValueError:
            error = elementName + " must be a number !"
                
    elif (elementType == "{0}:integer".format(defaultPrefix)):
        value = liElement[3].value
        try:
            int(value)
        except ValueError:
            error = elementName + " must be an integer !"
            
    elif (elementType == "{0}:string".format(defaultPrefix)):
        comparison = liElement[2].value
        value = liElement[3].value
        if (comparison == "like"):
            try:
                re.compile(value)
            except Exception, e:
                error = elementName + " must be a valid regular expression ! (" + str(e) + ")"    

    return error

def subElementfieldsToQuery(request, liElements, listLeavesId):
    
    mapTagIDElementInfo = request.session['mapTagIDElementInfoExplore'] 
    elemMatch = dict()
    i = 0
    
    firstElementPath = eval(mapTagIDElementInfo[str(listLeavesId[i])])['path']
    parentPath = "content." + ".".join(firstElementPath.split(".")[:-1])
    
    for li in liElements:        
        if (li[0].attrib['value'] == 'true'):
            boolComp = li[1].value
            if (boolComp == 'NOT'):
                isNot = True
            else:
                isNot = False
                
            elementInfo = ElementInfo(path=eval(mapTagIDElementInfo[str(listLeavesId[i])])['path'], type=eval(mapTagIDElementInfo[str(listLeavesId[i])])['type'])
            elementType = elementInfo.type
            elementName = elementInfo.path.split(".")[-1]
            if (elementType == "enum"):
                value = li[2].value            
                criteria = enumCriteria(elementName, value, isNot)
            else:                
                comparison = li[2].value
                value = li[3].value
                criteria = buildCriteria(request, elementName, comparison, value, elementType , isNot)
             
        
            elemMatch.update(criteria)
                
        i += 1
         
    query = dict()
    query[parentPath] = dict()
    query[parentPath]["$elemMatch"] = elemMatch
    
    
    return query


def subElementfieldsToPrettyQuery(request, liElements, listLeavesId):
    mapTagIDElementInfo = request.session['mapTagIDElementInfoExplore'] 
    
    query = ""
    
    elemMatch = "("
    i = 0
    
    for li in liElements:        
        if (li[0].attrib['value'] == 'true'):
            boolComp = li[1].value
            if (boolComp == 'NOT'):
                isNot = True
            else:
                isNot = False
                
            elementInfo = ElementInfo(path=eval(mapTagIDElementInfo[str(listLeavesId[i])])['path'], type=eval(mapTagIDElementInfo[str(listLeavesId[i])])['type'])
            elementType = elementInfo.type
            elementName = elementInfo.path.split(".")[-1]
            if (elementType == "enum"):
                value = li[2].value
                criteria = enumToPrettyCriteria(elementName, value, isNot)
            else:                 
                comparison = li[2].value
                value = li[3].value
                criteria = buildPrettyCriteria(elementName, comparison, value, isNot)
            
            if (elemMatch != "("):
                elemMatch += ", "
            elemMatch += criteria       
        i += 1
        
    elemMatch += ")"
    firstElementPath = eval(mapTagIDElementInfo[str(listLeavesId[0])])['path']
    parentName = firstElementPath.split(".")[-2]
    
    query =  parentName + elemMatch
        
    return query 
