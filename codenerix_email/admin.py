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

from django.conf import settings
from django.contrib import admin
from codenerix_email.models import EmailMessage, EmailAttachment, EmailTemplate, MODELS

admin.site.register(EmailMessage)
admin.site.register(EmailAttachment)
admin.site.register(EmailTemplate)


for info in MODELS:
    model = info[1]
    for lang in settings.LANGUAGES:
        lang_code = lang[0]
        query = "from .models import {}Text{}\n".format(model, lang_code.upper())
        query += "admin.site.register({}Text{})\n".format(model, lang_code.upper())
        exec(query)
