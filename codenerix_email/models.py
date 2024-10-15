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
#
# type: ignore

import re
import ssl
import smtplib
from uuid import uuid4

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db import models
from django.template import Context, Template
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db.models import Q

from codenerix.models import CodenerixModel
from codenerix_lib.debugger import Debugger
from codenerix.lib.genmail import (  # noqa: N817
    EmailMessage as EM,
    get_connection,
)
from codenerix.fields import WysiwygAngularField

CONTENT_SUBTYPE_PLAIN = "plain"
CONTENT_SUBTYPE_HTML = "html"
CONTENT_SUBTYPES = (
    (CONTENT_SUBTYPE_PLAIN, _("Plain")),
    (CONTENT_SUBTYPE_HTML, _("HTML Web")),
)


def ensure_header(headers, key, value):
    if key not in headers:
        headers[key] = value
    return headers


class EmailMessage(CodenerixModel, Debugger):
    uuid = models.UUIDField(
        _("UUID"),
        unique=True,
        default=uuid4,
        editable=False,
        null=False,
        blank=False,
    )
    efrom = models.EmailField(_("From"), blank=False, null=False)
    eto = models.EmailField(_("To"), blank=False, null=False)
    subject = models.CharField(
        _("Subject"), max_length=256, blank=False, null=False
    )
    body = models.TextField(_("Body"), blank=False, null=False)
    priority = models.PositiveIntegerField(
        _("Priority"), blank=False, null=False, default=5
    )
    sending = models.BooleanField(
        _("Sending"), blank=False, null=False, default=False
    )
    sent = models.BooleanField(
        _("Sent"), blank=False, null=False, default=False
    )
    error = models.BooleanField(
        _("Error"), blank=False, null=False, default=False
    )
    retries = models.PositiveIntegerField(
        _("Retries"), blank=False, null=False, default=0
    )
    next_retry = models.DateTimeField(_("Next retry"), auto_now_add=True)
    log = models.TextField(_("Log"), blank=True, null=True)
    opened = models.DateTimeField(
        _("Opened"), null=True, blank=True, default=None
    )
    content_subtype = models.CharField(
        _("Content Subtype"),
        max_length=256,
        choices=CONTENT_SUBTYPES,
        blank=False,
        null=False,
        default=CONTENT_SUBTYPE_HTML,
    )
    unsubscribe_url = models.URLField(
        _("Unsubscribe URL"), blank=True, null=True
    )
    headers = models.JSONField(_("Headers"), blank=True, null=True)

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
        fields.append(("retries", _("Retries")))
        fields.append(("next_retry", _("Next retry")))
        fields.append(("pk", _("ID")))
        fields.append(("uuid", _("UUID")))
        fields.append(("unsubscribe_url", _("Unsubscribe")))
        fields.append(("content_subtype", _("Content Subtype")))
        return fields

    def __searchQ__(self, info, search):  # noqa: N802
        answer = super().__searchQ__(info, search)
        answer["uuid"] = Q(uuid__icontains=search)
        answer["priority"] = Q(priority=search)
        # answer["efrom"] = Q(efrom__icontains=search)
        answer["eto"] = Q(eto__icontains=search)
        answer["retries"] = Q(retries=search)
        answer["pk"] = Q(pk=search)
        answer["unsubscribe_url"] = Q(unsubscribe_url__icontains=search)
        return answer

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
        }

    def __unicode__(self):
        return "{} ({})".format(self.eto, self.pk)

    def clean(self):
        if not isinstance(self.headers, dict):
            raise ValidationError(_("HEADERS must be a Dictionary"))

    def set_opened(self):
        if not self.opened:
            self.opened = timezone.now()
            self.save()

    def get_headers(self):

        # Get headers
        headers = self.headers or {}

        # Ensure unsubscribe headers
        if self.unsubscribe_url:
            ensure_header(
                headers, "List-Unsubscribe", f"<{self.unsubscribe_url}>"
            )
            ensure_header(
                headers, "List-Unsubscribe-Post", "List-Unsubscribe=One-Click"
            )

        # Return headers
        return headers

    @classmethod
    def process_queue(
        cls, connection=None, legacy=False, silent=True, debug=False
    ):
        """
        This method will process all the emails in the queue
        """

        # Process queue
        emails = cls.objects.filter(
            sent=False, error=False, next_retry__lte=timezone.now()
        )

        # Do we have to send emails
        if emails.count():

            # Get connection if not connected yet
            if connection is None:

                # Connect
                connection = cls.internal_connect(legacy)

            # Configure them as sending
            emails.update(sending=True)

            # Send them
            for email in emails.order_by("priority"):
                try:
                    email.send(
                        connection=connection,
                        legacy=legacy,
                        silent=silent,
                        debug=debug,
                    )
                except Exception as e:

                    # Los the error into this email
                    if email.log is None:
                        email.log = ""
                    email.log += f"Error: {e}\n"
                    email.sending = False
                    email.save()
                    email.warning(f"Error at EmailMessage<{{email.pk}}>: {e}")

                    # Set all emails to not sending, since we are stopping now
                    emails.update(sending=False)

                    # Re-raise the exception
                    raise

                emails.update(sending=False)

    @classmethod
    def internal_connect(cls, legacy=False):
        """
        This class will return a connection instance, you can disconnect it
        with connection.close()
        """

        if not legacy:
            host = settings.CLIENT_EMAIL_HOST
            port = settings.CLIENT_EMAIL_PORT
            username = settings.CLIENT_EMAIL_USERNAME
            password = settings.CLIENT_EMAIL_PASSWORD
            use_tls = settings.CLIENT_EMAIL_USE_TLS
        else:
            host = settings.EMAIL_HOST
            port = settings.EMAIL_PORT
            username = settings.EMAIL_USERNAME
            password = settings.EMAIL_PASSWORD
            use_tls = settings.EMAIL_USE_TLS

        # Remember last connection data
        connect_info = {
            "host": host,
            "port": port,
            "use_tls": use_tls,
            "legacy": legacy,
        }
        # Get connection
        return (
            get_connection(
                host=host,
                port=port,
                username=username,
                password=password,
                use_tls=use_tls,
            ),
            connect_info,
        )

    def connect(self, legacy=False):
        (connection, self.__connect_info) = EmailMessage.internal_connect(
            legacy
        )
        return connection

    def send(
        self,
        connection=None,
        legacy=False,
        silent=True,
        debug=False,
        content_subtype=None,
    ):

        # Autoconfigure Debugger
        if debug:
            self.set_name("EmailMessage")
            self.set_debug()

        # Warn about subtype
        if content_subtype:
            self.warning(
                _(
                    "Programming ERROR: You are using content_subtype, this "
                    "value has been DEPRECATED and will be remove in future "
                    "versions."
                )
            )

        # Get connection if not connected yet
        if connection is None:
            # Connect
            if not silent or debug:
                self.warning("Not connected, connecting...")
            connection = self.connect(legacy)

        if self.eto:
            if debug:
                self.set_name("EmailMessage->{}".format(self.eto))

            # Manually open the connection
            error = None
            try:
                connection.open()
            except (
                smtplib.SMTPAuthenticationError,
                OSError,
                TimeoutError,
            ) as e:
                connection = None
                exceptiontxt = str(type(e)).split(".")[-1].split("'")[0]
                ci = getattr(self, "__connect_info", {})
                error = "{}: {} [HOST={}:{} TLS={}]\n".format(
                    exceptiontxt,
                    e,
                    ci.get("host", "-"),
                    ci.get("port", "-"),
                    ci.get("use_tls", "-"),
                )
                if not silent or debug:
                    self.warning(error)
                if self.log is None:
                    self.log = ""
                self.log += f"{error}\n"
                # We will not retry anymore (for now)
                self.sending = False
                # We make lower this email's priority
                self.priority += 1
                # Set we just made a new retry
                self.retries += 1
                self.next_retry = timezone.now() + timezone.timedelta(
                    seconds=getattr(
                        settings, "CLIENT_EMAIL_RETRIES_WAIT", 5400
                    )
                )  # retry every 1.5h
                if self.retries >= getattr(
                    settings, "CLIENT_EMAIL_RETRIES", 10
                ):  # 10 retries * 1.5h = 15h
                    self.error = True
                # Save all
                self.save()
                if not silent:
                    raise

            if connection:

                email = EM(
                    subject=self.subject,
                    body=self.body,
                    from_email=self.efrom,
                    to=[self.eto],
                    connection=connection,
                    headers=self.get_headers(),
                )
                email.content_subtype = self.content_subtype
                for at in self.attachments.all():
                    with open(at.path) as f:
                        email.attach(at.filename, f.read(), at.mime)

                # send list emails
                retries = 1
                while retries + 1:
                    error = None
                    try:
                        if connection.send_messages([email]):
                            # We are done
                            self.sent = True
                            self.sending = False
                            break
                    except ssl.SSLError as e:
                        error = f"SSLError: {e}\n"
                        if not silent or debug:
                            self.warning(error)
                        if self.log is None:
                            self.log = ""
                        self.log += f"{error}\n"
                    except smtplib.SMTPServerDisconnected as e:
                        error = f"SMTPServerDisconnected: {e}\n"
                        if not silent or debug:
                            self.warning(error)
                        if self.log is None:
                            self.log = ""
                        self.log += f"{error}\n"
                        try:
                            connection.open()
                            error = None
                        except (
                            smtplib.SMTPAuthenticationError,
                            OSError,
                            TimeoutError,
                        ) as e:
                            error = f"SMTPServerReconnect: {e}\n"
                            if not silent or debug:
                                self.warning(error)
                            if self.log is None:
                                self.log = ""
                            self.log += f"{error}\n"
                    except smtplib.SMTPException as e:
                        error = f"SMTPException: {e}\n"
                        if not silent or debug:
                            self.warning(error)
                        if self.log is None:
                            self.log = ""
                        self.log += f"{error}\n"
                    finally:
                        # One chance less
                        retries -= 1
                        # Check if this is the last try
                        if not retries:
                            # We will not retry anymore (fow now)
                            self.sending = False
                            # We make lower this email's priority
                            self.priority += 1
                            # Set we just made a new retry
                            self.retries += 1
                            self.next_retry = (
                                timezone.now()
                                + timezone.timedelta(
                                    seconds=getattr(
                                        settings,
                                        "CLIENT_EMAIL_RETRIES_WAIT",
                                        5400,
                                    )
                                )
                            )  # retry every 1.5h
                            if self.retries >= getattr(
                                settings, "CLIENT_EMAIL_RETRIES", 10
                            ):  # 10 retries * 1.5h = 15h
                                self.error = True
                        # Save the email
                        self.save()
                        # Disconnect
                        connection.close()
                        # Connect
                        connection = self.connect(legacy)


class EmailAttachment(CodenerixModel):
    email = models.ForeignKey(
        EmailMessage,
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        related_name="attachments",
    )
    filename = models.CharField(
        _("Filename"), max_length=256, blank=False, null=False
    )
    mime = models.CharField(
        _("Mimetype"), max_length=256, blank=False, null=False
    )
    path = models.FileField(_("Path"), blank=False, null=False)

    def __fields__(self, info):
        fields = []
        fields.append(("email", _("Email"), 100))
        fields.append(("filename", _("Filename"), 100))
        fields.append(("mime", _("Mimetype"), 100))
        fields.append(("path", _("Path"), 100))
        return fields


class EmailTemplate(CodenerixModel):
    cid = models.CharField(
        _("CID"), unique=True, max_length=30, blank=False, null=False
    )
    efrom = models.TextField(_("From"), blank=True, null=False)
    content_subtype = models.CharField(
        _("Content Subtype"),
        max_length=256,
        choices=CONTENT_SUBTYPES,
        blank=False,
        null=False,
        default=CONTENT_SUBTYPE_HTML,
    )

    def __fields__(self, info):
        fields = []
        fields.append(("pk", _("PK"), 100))
        fields.append(("cid", _("CID"), 100))
        fields.append(("efrom", _("From"), 100))
        fields.append(("content_subtype", _("Content Subtype"), 100))
        return fields

    def __str__(self):
        return "{}:{}".format(self.cid, self.pk)

    def __unicode__(self):
        return self.__str__()

    @staticmethod
    def get(cid=None, context={}, pk=None, lang=None):
        """
        Usages:
            EmailTemplate.get('PACO', ctx) => EmailMessage(): le falta el eto
            > cid: PACO
            EmailTemplate.get(pk='PACO', context=ctx) => EmailMessage(): le
            falta el eto
            > pk: PACO    (we don't have CID)
        """
        if cid:
            template = EmailTemplate.objects.filter(cid=cid).first()
        else:
            template = EmailTemplate.objects.filter(pk=pk).first()

        if template:
            return template.get_email(context, lang)
        else:
            return None

    def get_email(self, context, lang=None):
        if lang is None:
            lang = settings.LANGUAGES_DATABASES[0].lower()

        e = EmailMessage()
        context["CDNX_EMAIL_emsg_uuid"] = e.uuid
        e.subject = Template(getattr(self, lang).subject).render(
            Context(context)
        )
        e.body = Template(getattr(self, lang).body).render(Context(context))
        e.efrom = Template(self.efrom).render(Context(context))
        e.content_subtype = self.content_subtype
        return e

    def clean(self):
        if self.cid:
            self.cid = self.cid.upper()
            if len(re.findall(r"[A-Za-z0-9]+", self.cid)) != 1:
                raise ValidationError(
                    _(
                        "CID can contains only number and letters with "
                        "no spaces"
                    )
                )


class GenText(CodenerixModel):  # META: Abstract class
    class Meta(CodenerixModel.Meta):
        abstract = True

    subject = models.TextField(_("Subject"), blank=True, null=False)
    body = WysiwygAngularField(_("Body"), blank=True, null=False)

    def __fields__(self, info):
        fields = []
        fields.append(("subject", _("Subject"), 100))
        fields.append(("body", _("Body"), 100))
        return fields

    def __unicode__(self):
        return "{}".format(self.subject)

    def __str__(self):
        return self.__unicode__()


MODELS = [
    ("email_template", "EmailTemplate"),
]

for info in MODELS:
    field = info[0]
    model = info[1]
    for lang_code in settings.LANGUAGES_DATABASES:
        query = f"class {model}Text{lang_code}(GenText):\n"
        query += (
            f"  {field} = models.OneToOneField({model}, "
            f"on_delete=models.CASCADE, blank=False, null=False, "
            f"related_name='{lang_code.lower()}')\n"
        )
        exec(query)
