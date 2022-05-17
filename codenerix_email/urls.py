# -*- coding: utf-8 -*-
#
# django-codenerix-email
#
# Codenerix GNU
#
# Project URL : http://www.codenerix.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.urls import re_path
from codenerix_email.views import EmailTemplateList, EmailTemplateCreate, EmailTemplateCreateModal, EmailTemplateUpdate, EmailTemplateUpdateModal, EmailTemplateDelete
from codenerix_email.views import EmailMessageList, EmailMessageCreate, EmailMessageCreateModal, EmailMessageUpdate, EmailMessageUpdateModal, EmailMessageDelete, EmailMessageDetails


urlpatterns = [
    re_path(r'^emailtemplates$', EmailTemplateList.as_view(), name='CDNX_emails_emailtemplates_list'),
    re_path(r'^emailtemplates/add$', EmailTemplateCreate.as_view(), name='CDNX_emails_emailtemplates_add'),
    re_path(r'^emailtemplates/addmodal$', EmailTemplateCreateModal.as_view(), name='CDNX_emails_emailtemplates_addmodal'),
    re_path(r'^emailtemplates/(?P<pk>\w+)/edit$', EmailTemplateUpdate.as_view(), name='CDNX_emails_emailtemplates_edit'),
    re_path(r'^emailtemplates/(?P<pk>\w+)/editmodal$', EmailTemplateUpdateModal.as_view(), name='CDNX_emails_emailtemplates_editmodal'),
    re_path(r'^emailtemplates/(?P<pk>\w+)/delete$', EmailTemplateDelete.as_view(), name='CDNX_emails_emailtemplates_delete'),

    re_path(r'^emailmessages$', EmailMessageList.as_view(), name='CDNX_emails_emailmessages_list'),
    re_path(r'^emailmessages/add$', EmailMessageCreate.as_view(), name='CDNX_emails_emailmessages_add'),
    re_path(r'^emailmessages/addmodal$', EmailMessageCreateModal.as_view(), name='CDNX_emails_emailmessages_addmodal'),
    re_path(r'^emailmessages/(?P<pk>\w+)$', EmailMessageDetails.as_view(), name='CDNX_emails_emailmessages_details'),
    re_path(r'^emailmessages/(?P<pk>\w+)/edit$', EmailMessageUpdate.as_view(), name='CDNX_emails_emailmessages_edit'),
    re_path(r'^emailmessages/(?P<pk>\w+)/editmodal$', EmailMessageUpdateModal.as_view(), name='CDNX_emails_emailmessages_editmodal'),
    re_path(r'^emailmessages/(?P<pk>\w+)/delete$', EmailMessageDelete.as_view(), name='CDNX_emails_emailmessages_delete'),
]
