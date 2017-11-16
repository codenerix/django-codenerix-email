# -*- coding: utf-8 -*-
#
# django-codenerix-email
#
# Copyright 2017 Centrologic Computational Logistic Center S.L.
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

from django.conf.urls import url
from codenerix_email.views import EmailTemplateList, EmailTemplateCreate, EmailTemplateCreateModal, EmailTemplateUpdate, EmailTemplateUpdateModal, EmailTemplateDelete
from codenerix_email.views import EmailMessageList, EmailMessageCreate, EmailMessageCreateModal, EmailMessageUpdate, EmailMessageUpdateModal, EmailMessageDelete, EmailMessageDetails


urlpatterns = [
    url(r'^emailtemplates$', EmailTemplateList.as_view(), name='CDNX_emails_emailtemplates_list'),
    url(r'^emailtemplates/add$', EmailTemplateCreate.as_view(), name='CDNX_emails_emailtemplates_add'),
    url(r'^emailtemplates/addmodal$', EmailTemplateCreateModal.as_view(), name='CDNX_emails_emailtemplates_addmodal'),
    url(r'^emailtemplates/(?P<pk>\w+)/edit$', EmailTemplateUpdate.as_view(), name='CDNX_emails_emailtemplates_edit'),
    url(r'^emailtemplates/(?P<pk>\w+)/editmodal$', EmailTemplateUpdateModal.as_view(), name='CDNX_emails_emailtemplates_editmodal'),
    url(r'^emailtemplates/(?P<pk>\w+)/delete$', EmailTemplateDelete.as_view(), name='CDNX_emails_emailtemplates_delete'),

    url(r'^emailmessages$', EmailMessageList.as_view(), name='CDNX_emails_emailmessages_list'),
    url(r'^emailmessages/add$', EmailMessageCreate.as_view(), name='CDNX_emails_emailmessages_add'),
    url(r'^emailmessages/addmodal$', EmailMessageCreateModal.as_view(), name='CDNX_emails_emailmessages_addmodal'),
    url(r'^emailmessages/(?P<pk>\w+)$', EmailMessageDetails.as_view(),name='CDNX_emails_emailmessages_details'),
    url(r'^emailmessages/(?P<pk>\w+)/edit$', EmailMessageUpdate.as_view(), name='CDNX_emails_emailmessages_edit'),
    url(r'^emailmessages/(?P<pk>\w+)/editmodal$', EmailMessageUpdateModal.as_view(), name='CDNX_emails_emailmessages_editmodal'),
    url(r'^emailmessages/(?P<pk>\w+)/delete$', EmailMessageDelete.as_view(), name='CDNX_emails_emailmessages_delete'),
]
