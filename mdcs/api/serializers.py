################################################################################
#
# File Name: serializers.py
# Application: api
# Purpose:   
#
# Author: Sharief Youssef
#         sharief.youssef@nist.gov
#
#         Guillaume SOUSA AMARAL
#         guillaume.sousa@nist.gov
#
# Sponsor: National Institute of Standards and Technology (NIST)
#
################################################################################

from rest_framework import serializers
from rest_framework_mongoengine.serializers import MongoEngineModelSerializer
from mgi.models import SavedQuery, Template, Ontology

class jsonDataSerializer(serializers.Serializer):
    title = serializers.CharField()
    schema = serializers.CharField()
    content = serializers.CharField()
    _id = serializers.CharField(required=False)
    
class savedQuerySerializer(MongoEngineModelSerializer):
    class Meta:
        model = SavedQuery
        
class querySerializer(serializers.Serializer):
    query = serializers.CharField()

class sparqlQuerySerializer(serializers.Serializer):
    query = serializers.CharField()
    format = serializers.CharField(required=False)
    
class sparqlResultsSerializer(serializers.Serializer):
    content = serializers.CharField()

class schemaSerializer(MongoEngineModelSerializer):
    class Meta:
        model = Template
        exclude = (['templateVersion','version'])

class templateSerializer(serializers.Serializer):
    title = serializers.CharField()
    filename = serializers.CharField()
    content = serializers.CharField()
    templateVersion = serializers.CharField()
    version = serializers.IntegerField()
    id = serializers.CharField(required=False)
    
class ontologySerializer(MongoEngineModelSerializer):
    class Meta:
        model = Ontology
        exclude = (['ontologyVersion','version'])
        
class resOntologySerializer(serializers.Serializer):
    title = serializers.CharField()
    filename = serializers.CharField()
    content = serializers.CharField()
    ontologyVersion = serializers.CharField()
    version = serializers.IntegerField()
    id = serializers.CharField(required=False)
        