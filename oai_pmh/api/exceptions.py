################################################################################
#
# File Name: exceptions.py
# Application: Informatics Core
# Description: All OAI-PMH exceptions
#
# Author: Pierre Francois RIGODIAT
#         pierre-francois.rigodiat@nist.gov
#
# Sponsor: National Institute of Standards and Technology (NIST)
#
################################################################################
from rest_framework.response import Response
from oai_pmh.api.messages import APIMessage

class OAIAPIException(Exception):
    def __init__(self, message, status):
        self.message = message
        self.status = status

    def __str__(self):
        return repr(self.message)

    def response(self):
        return Response(self.message, status=self.status)


class OAIAPILabelledException(OAIAPIException):
    def response(self):
        return Response(APIMessage.getMessageLabelled(self.message), status=self.status)