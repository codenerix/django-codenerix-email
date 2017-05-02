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

from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from codenerix.forms import GenModelForm
from codenerix.widgets import WysiwygAngularInput
from codenerix_email.models import EmailTemplate, MODELS


class EmailTemplateForm(GenModelForm):
    class Meta:
        model = EmailTemplate
        exclude = []

    def __groups__(self):
        return [(_(u'Details'), 12,
            ['cid', 3],
            ['efrom', 9],
        )
        ]

    @staticmethod
    def __groups_details__():
        return [(_(u'Details'), 12,
            ['cid', 3],
            ['efrom', 9],)
        ]


for info in MODELS:
    field = info[0]
    model = info[1]
    for lang_code in settings.LANGUAGES_DATABASES:
        query = "from codenerix_email.models import {}Text{}\n".format(model, lang_code)
        exec(query)
        query = """
class {model}TextForm{lang}(GenModelForm):\n
    class Meta:\n
        model={model}Text{lang}\n
        exclude = []\n
        widgets = {{\n
            'subject': WysiwygAngularInput(),\n
            'body': WysiwygAngularInput(),\n
        }}\n
    def __groups__(self):\n
        return [(_('Details'),12,"""

        if lang_code == settings.LANGUAGES_DATABASES[0]:
            query += """
                ['subject', 12, None, None, None, None, None, ["ng-blur=refresh_lang_field('title', '{model}TextForm', [{languages}])"]],
                ['body', 12, None, None, None, None, None, ["ng-blur=refresh_lang_field('url', '{model}TextForm', [{languages}])"]],
            )]\n"""
        else:
            query += """
                ['subject', 12],
                ['body', 12],
                )]\n"""
        exec(query.format(model=model, lang=lang_code, languages="'{}'".format("','".join(settings.LANGUAGES_DATABASES))))
