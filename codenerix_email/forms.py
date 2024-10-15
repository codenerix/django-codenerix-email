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

from django.utils.translation import gettext_lazy as _
from django.conf import settings

from codenerix.forms import GenModelForm
from codenerix.widgets import WysiwygAngularInput
from codenerix_email.models import EmailTemplate, EmailMessage, MODELS


class EmailTemplateForm(GenModelForm):
    class Meta:
        model = EmailTemplate
        exclude = []

    def __groups__(self):
        return [
            (
                _("Details"),
                12,
                (
                    None,
                    3,
                    ["cid", 12],
                    ["content_subtype", 12],
                ),
                (
                    None,
                    9,
                    ["efrom", 9],
                ),
            ),
        ]

    @staticmethod
    def __groups_details__():
        return [
            (
                _("Details"),
                12,
                ["cid", 3],
                ["efrom", 9],
            )
        ]


class EmailMessageForm(GenModelForm):
    class Meta:
        model = EmailMessage
        exclude = ["sending", "log"]

    def __groups__(self):
        return [
            (
                _("Details"),
                12,
                ["efrom", 2],
                ["eto", 2],
                ["subject", 4],
                ["priority", 1],
                ["sent", 1],
                ["error", 1],
                ["retries", 1],
                ["body", 12],
            )
        ]

    @staticmethod
    def __groups_details__():
        return [
            (
                _("Details"),
                6,
                ["uuid", 3],
                ["created", 3],
                ["updated", 3],
                ["efrom", 3],
                ["eto", 3],
                ["subject", 3],
                ["opened", 3],
                ["content_subtype", 3],
            ),
            (
                _("System"),
                6,
                ["sending", 3],
                ["sent", 3],
                ["error", 3],
                ["retries", 3],
                ["priority", 3],
                ["log", 3],
                ["unsubscribe_url", 3],
                ["headers", 3],
            ),
            (
                _("Body"),
                12,
                ["body", 3],
            ),
        ]


for info in MODELS:
    field = info[0]
    model = info[1]
    for lang_code in settings.LANGUAGES_DATABASES:
        query = "from codenerix_email.models import {}Text{}\n".format(
            model, lang_code
        )
        exec(query)
        query = """
class {model}TextForm{lang}(GenModelForm):\n
    class Meta:\n
        model={model}Text{lang}\n
        exclude = []\n
    def __groups__(self):\n
        return [(_('Details'),12,"""

        if lang_code == settings.LANGUAGES_DATABASES[0]:
            query += """
                ['subject', 12, None, None, None, None, None, ["ng-change=refresh_lang_field('subject', '{model}TextForm', [{languages}])"]],
                ['body', 12, None, None, None, None, None, ["ng-blur=refresh_lang_field('body', '{model}TextForm', [{languages}])"]],
            )]\n"""
        else:
            query += """
                ['subject', 12],
                ['body', 12],
                )]\n"""
        exec(
            query.format(
                model=model,
                lang=lang_code,
                languages="'{}'".format(
                    "','".join(settings.LANGUAGES_DATABASES)
                ),
            )
        )
