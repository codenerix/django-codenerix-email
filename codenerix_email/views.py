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

from django.utils.translation import ugettext as _
from django.conf import settings

from codenerix.multiforms import MultiForm
from codenerix.views import GenList, GenCreate, GenCreateModal, GenUpdate, GenUpdateModal, GenDelete
from codenerix_email.models import EmailTemplate, MODELS
from codenerix_email.forms import EmailTemplateForm

formsfull = {}

for info in MODELS:
    field = info[0]
    model = info[1]
    formsfull[model] = [(None, None, None)]
    for lang_code in settings.LANGUAGES_DATABASES:
        query = "from codenerix_email.models import {}Text{}\n".format(model, lang_code)
        query += "from codenerix_email.forms import {}TextForm{}".format(model, lang_code)
        exec(query)

        formsfull[model].append((eval("{}TextForm{}".format(model, lang_code.upper())), field, None))


# ############################################
# EmailTemplate
class EmailTemplateList(GenList):
    model = EmailTemplate
    extra_context = {
        'menu': ['EmailTemplate', 'people'],
        'bread': [_('EmailTemplate'), _('People')]
    }


class EmailTemplateCreate(MultiForm, GenCreate):
    model = EmailTemplate
    form_class = EmailTemplateForm
    forms = formsfull["EmailTemplate"]


class EmailTemplateCreateModal(GenCreateModal, EmailTemplateCreate):
    pass


class EmailTemplateUpdate(MultiForm, GenUpdate):
    model = EmailTemplate
    form_class = EmailTemplateForm
    forms = formsfull["EmailTemplate"]


class EmailTemplateUpdateModal(GenUpdateModal, EmailTemplateUpdate):
    pass


class EmailTemplateDelete(GenDelete):
    model = EmailTemplate
