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

import base64

from typing import Optional, Tuple, List, Dict
from django.http import HttpResponse
from django.views.generic import View

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.conf import settings
from django.http import HttpRequest, Http404

from codenerix.multiforms import MultiForm  # type: ignore
from codenerix.views import (  # type: ignore
    GenList,
    GenCreate,
    GenCreateModal,
    GenUpdate,
    GenUpdateModal,
    GenDelete,
    GenDetail,
)
from codenerix_email.models import EmailTemplate, EmailMessage, MODELS
from codenerix_email.forms import EmailTemplateForm, EmailMessageForm

formsfull: Dict[
    str,
    List[
        Tuple[
            Optional[HttpRequest],
            Optional[str],
            Optional[str],
        ]
    ],
] = {}

for info in MODELS:
    field = info[0]
    model = info[1]
    formsfull[model] = [(None, None, None)]
    for lang_code in settings.LANGUAGES_DATABASES:
        query = "from codenerix_email.models import {}Text{}\n".format(
            model, lang_code
        )
        query += "from codenerix_email.forms import {}TextForm{}".format(
            model, lang_code
        )
        exec(query)

        formsfull[model].append(
            (
                eval("{}TextForm{}".format(model, lang_code.upper())),
                field,
                None,
            )
        )


# ############################################
# EmailFollow
class EmailFollow(View):
    def get(self, request, *args, **kwargs):

        # Get uuid from email
        uid = kwargs.get("uuid_ext", None)

        if uid:

            # Get email message or return 404
            email_message = get_object_or_404(EmailMessage, uuid=uid)

            # Set email message as opened
            email_message.set_opened()

            # Return an image of 1x1 pixel
            return HttpResponse(
                base64.b64decode(
                    "R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="
                ),
                content_type="image/gif",
            )

        else:

            # Return 404
            raise Http404


# ############################################
# EmailTemplate
class EmailTemplateList(GenList):
    model = EmailTemplate
    extra_context = {
        "menu": ["codenerix_email", "emailtemplate"],
        "bread": [_("Emails"), _("Email Template")],
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


# ############################################
# EmailMessage
class EmailMessageList(GenList):
    model = EmailMessage
    show_details = True
    search_filter_button = True
    datetime_filter = "updated"
    default_ordering = ["-created"]
    static_partial_row = "codenerix_email/partials/emailmessages_rows.html"
    gentranslate = {
        "sending": _("Sending"),
        "sent": _("Sent"),
        "notsent": _("Not sent!"),
        "waiting": _("Waiting"),
    }
    extra_context = {
        "menu": ["codenerix_email", "emailmessages"],
        "bread": [_("Emails"), _("Email Messages")],
    }


class EmailMessageCreate(GenCreate):
    model = EmailMessage
    form_class = EmailMessageForm


class EmailMessageCreateModal(GenCreateModal, EmailMessageCreate):
    pass


class EmailMessageDetails(GenDetail):
    model = EmailMessage
    groups = EmailMessageForm.__groups_details__()
    show_details = True


class EmailMessageUpdate(GenUpdate):
    model = EmailMessage
    form_class = EmailMessageForm
    show_details = True


class EmailMessageUpdateModal(GenUpdateModal, EmailMessageUpdate):
    pass


class EmailMessageDelete(GenDelete):
    model = EmailMessage
