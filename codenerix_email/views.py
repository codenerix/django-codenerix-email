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
from django.db.models import Q, Count

from codenerix.multiforms import MultiForm  # type: ignore
from codenerix.views import (  # type: ignore
    GenList,
    GenCreate,
    GenCreateModal,
    GenUpdate,
    GenUpdateModal,
    GenDelete,
    GenDetail,
    GenDetailModal,
    SearchFilters,
)
from codenerix_email.models import (
    EmailTemplate,
    EmailMessage,
    EmailReceived,
    MODELS,
    BOUNCE_SOFT,
    BOUNCE_HARD,
)
from codenerix_email.forms import (
    EmailTemplateForm,
    EmailMessageForm,
    EmailReceivedForm,
)

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
    default_ordering = ["-created"]
    extra_context = {
        "menu": ["codenerix_email", "emailtemplate"],
        "bread": [_("Emails"), _("Email Template")],
    }

    def __fields__(self, info):
        fields = []
        fields.append(("pk", _("PK"), 100))
        fields.append(("cid", _("CID"), 100))
        fields.append(("efrom", _("From"), 100))
        fields.append(
            (
                f"{self.language}__subject",
                _("Subject"),
                100,
                None,
                "shorttext:150",
            )
        )
        fields.append(("content_subtype", _("Content Subtype"), 100))
        return fields


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
    annotations = {
        # "bounces_soft_count": Count(
        #     "receiveds__pk", filter=Q(receiveds__bounce_type=BOUNCE_SOFT)
        # ),
        # "bounces_hard_count": Count(
        #     "receiveds__pk", filter=Q(receiveds__bounce_type=BOUNCE_HARD)
        # ),
        "bounces_total_count": Count(
            "receiveds__pk", filter=Q(receiveds__bounce_type__isnull=False)
        ),
    }

    def __fields__(self, info):
        fields = []
        fields.append(("sending", None))
        fields.append(("error", None))
        fields.append(("sent", _("Send")))
        fields.append(("priority", _("Priority")))
        fields.append(("created", _("Created")))
        fields.append(("updated", _("Updated")))
        fields.append(("opened", _("Opened")))
        # fields.append(("efrom", _("From")))
        fields.append(("eto", _("To")))
        fields.append(("subject", _("Subject")))
        fields.append(("bounces_total_count", _("Bounces")))
        # fields.append(("bounces_soft_count", _("Soft bounces")))
        # fields.append(("bounces_hard_count", _("Hard bounces")))
        fields.append(("retries", _("Retries")))
        fields.append(("next_retry", _("Next retry")))
        fields.append(("pk", _("ID")))
        fields.append(("uuid", _("UUID")))
        fields.append(("unsubscribe_url", _("Unsubscribe")))
        fields.append(("content_subtype", _("Content Subtype")))
        return fields

    def __searchF__(self, info):  # noqa: N802
        def mailstatus(x):
            if x == "D":
                return Q(error=False, sent=True)
            elif x == "P":
                return Q(error=False, sent=False, sending=False)
            elif x == "S":
                return Q(error=False, sent=False, sending=True)
            elif x == "E":
                return Q(error=True)
            else:
                return Q()

        mailoptions = [
            ("D", _("Sent")),  # Sent - Done
            ("P", _("Pending")),  # Pending - Pending
            ("S", _("Sending")),  # Sending - Sending
            ("E", _("Error")),  # Error - Error
        ]

        return {
            "sent": (_("Sent"), lambda x: mailstatus(x), mailoptions),
            "uuid": (_("UUID"), lambda x: Q(uuid__icontains=x), "input"),
            "priority": (_("Priority"), lambda x: Q(priority=x), "input"),
            "opened": (
                _("Opened"),
                lambda x: ~Q(opened__isnull=x),
                [(True, _("Yes")), (False, _("No"))],
            ),
            # "efrom": (_("From"), lambda x: Q(efrom__icontains=x), "input"),
            "eto": (_("To"), lambda x: Q(eto__icontains=x), "input"),
            "retries": (_("Retries"), lambda x: Q(retries=x), "input"),
            "pk": (_("ID"), lambda x: Q(pk=x), "input"),
            "bounces_total_count": (
                _("Bounces"),
                SearchFilters.number("bounces_total_count"),
                "input",
            ),
            "bounces_soft_count": (
                _("Soft bounces"),
                SearchFilters.number("bounces_soft_count"),
                "input",
            ),
            "bounces_hard_count": (
                _("Hard bounces"),
                SearchFilters.number("bounces_hard_count"),
                "input",
            ),
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
    tabs = [
        {
            "id": "receiveds",
            "name": _("Received"),
            "ws": "CDNX_emails_emailreceiveds_sublist",
            "rows": "base",
        }
    ]


class EmailMessageDetailsModal(EmailMessageDetails, GenDetailModal):
    pass


class EmailMessageUpdate(GenUpdate):
    model = EmailMessage
    form_class = EmailMessageForm
    show_details = True


class EmailMessageUpdateModal(GenUpdateModal, EmailMessageUpdate):
    pass


class EmailMessageDelete(GenDelete):
    model = EmailMessage


# ############################################
# EmailReceived
class EmailReceivedList(GenList):
    model = EmailReceived
    show_details = True
    search_filter_button = True
    datetime_filter = "updated"
    default_ordering = ["-created"]
    readonly = True
    gentranslate = {
        "sending": _("Sending"),
        "sent": _("Sent"),
        "notsent": _("Not sent!"),
        "waiting": _("Waiting"),
    }
    extra_context = {
        "menu": ["codenerix_email", "emailreceiveds"],
        "bread": [_("Emails"), _("Email Messages")],
    }


class EmailReceivedDetails(GenDetail):
    model = EmailReceived
    groups = EmailReceivedForm.__groups_details__()
    show_details = True
    readonly = True


class EmailReceivedDetailsModal(EmailReceivedDetails, GenDetailModal):
    pass


class EmailReceivedSubList(EmailReceivedList):
    def __limitQ__(self, info):  # noqa: N802
        limit = {}
        pk = info.kwargs.get("pk", None)
        limit["receiveds"] = Q(email__pk=pk)
        return limit
