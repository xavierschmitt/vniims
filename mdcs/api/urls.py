################################################################################
#
# File Name: urls.py
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

from django.conf.urls import patterns, url, include
# from api.views import JsonDataList
from api.views import docs, ping

urlpatterns = patterns(
    'api.views',
    url(r'^saved_queries/select/all$','select_all_savedqueries'),
    url(r'^saved_queries/select$','select_savedquery'),
    url(r'^saved_queries/delete$','delete_savedquery'),
    url(r'^saved_queries/add$','add_savedquery'),
    url(r'^curate$', 'curate', name='curate'),
    url(r'^explore/select/all$', 'explore', name='explore'),
    url(r'^explore/select$', 'explore_detail', name='explore_detail'),
    url(r'^explore/delete$', 'explore_delete', name='explore_delete'),
    url(r'^explore/query-by-example$', 'query_by_example', name='query_by_example'),
    url(r'^explore/sparql-query$', 'sparql_query', name='sparql_query'),
    url(r'^templates/add$','add_schema', name='add_schema'),
    url(r'^templates/select$','select_schema'),
    url(r'^templates/delete$','delete_schema'),
    url(r'^templates/restore$','restore_schema'),
    url(r'^templates/select/all$','select_all_schemas'),
    url(r'^templates/versions/select/all$','select_all_schemas_versions'),
    url(r'^templates/versions/current$','current_template_version'),
    url(r'^types/add$','add_type', name='add_type'),
    url(r'^types/select$','select_type'),
    url(r'^types/delete$','delete_type'),
    url(r'^types/restore$','restore_type'),
    url(r'^types/select/all$','select_all_types'),
    url(r'^types/versions/select/all$','select_all_types_versions'),
    url(r'^types/versions/current$','current_type_version'),
    url(r'^repositories/select/all$','select_all_repositories'),
    url(r'^repositories/select','select_repository'),
    url(r'^repositories/add$','add_repository'),
    url(r'^repositories/delete$','delete_repository'),
    url(r'^repositories/update$','update_repository'),
    url(r'^users/select/all$','select_all_users'),
    url(r'^users/select','select_user'),
    url(r'^users/add$','add_user'),
    url(r'^users/delete$','delete_user'),
    url(r'^users/update$','update_user'),
    url(r'^template/get-file$','get_file'),
    url(r'^type/get-dependency$','get_dependency'),
    url('', include([url(r'^ping$', ping)], namespace='ping')),
    url(r'^.*$', include([url(r'', docs)], namespace='error_redirect')),    
)


