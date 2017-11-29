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

import re
import ssl
import smtplib

from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.template import Context, Template
from django.core.exceptions import ValidationError
from django.conf import settings

from codenerix.models import CodenerixModel
from codenerix.lib.debugger import Debugger
from codenerix.lib.genmail import EmailMessage as EM, get_connection
from codenerix.fields import WysiwygAngularField


class EmailMessage(CodenerixModel, Debugger):
    efrom = models.EmailField(_('From'), blank=False, null=False)
    eto = models.EmailField(_('To'), blank=False, null=False)
    subject = models.CharField(_('Subject'), max_length=256, blank=False, null=False)
    body = models.TextField(_('Body'), blank=False, null=False)
    priority = models.PositiveIntegerField(_('Priority'), blank=False, null=False, default=5)
    sending = models.BooleanField(_('Sending'), blank=False, null=False, default=False)
    sent = models.BooleanField(_('Sent'), blank=False, null=False, default=False)
    error = models.BooleanField(_('Error'), blank=False, null=False, default=False)
    retries = models.PositiveIntegerField(_('Retries'), blank=False, null=False, default=0)
    next_retry = models.DateTimeField(_("Next retry"),  auto_now_add=True)
    log = models.TextField(_('Log'), blank=True, null=True)

    def __fields__(self, info):
        fields = []
        fields.append(('sending', None, 100))
        fields.append(('error', None, 100))
        fields.append(('sent', _('Send'), 100))
        fields.append(('priority', _('Priority'), 100))
        fields.append(('created', _('Created'), 100))
        fields.append(('efrom', _('From'), 100))
        fields.append(('eto', _('To'), 100))
        fields.append(('subject', _('Subject'), 100))
        fields.append(('retries', _('Retries'), 100))
        fields.append(('next_retry', _('Next retry'), 100))
        fields.append(('pk', _("ID"), 100))
        return fields

    def __unicode__(self):
        return "{} ({})".format(self.eto, self.pk)

    def connect(self, legacy=False):
        '''
        This class will return a connection instance, you can disconnect it with connection.close()
        '''

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

        # Get connection
        return get_connection(host=host, port=port, username=username, password=password, use_tls=use_tls)

    def send(self, connection=None, legacy=False, silent=True, debug=False):

        # Autoconfigure Debugger
        if debug:
            self.set_name("EmailMessage")
            self.set_debug()

        # Get connection if not connected yet
        if connection is None:
            # Connect
            self.warning("Not connected, connecting...")
            connection = self.connect(legacy)

        if self.eto:
            if debug:
                self.set_name("EmailMessage->{}".format(self.eto))

            # Manually open the connection
            try:
                connection.open()
            except smtplib.SMTPAuthenticationError as e:
                connection = None
                if self.log is None:
                    self.log = ''
                error = u"SMTPAuthenticationError: {}\n".format(e)
                self.warning(error)
                self.log += error
                # We will not retry anymore
                self.sending = False
                # We make lower this email's priority
                self.priority += 1
                # Set new retry
                self.retries += 1
                self.next_retry = timezone.now() + timezone.timedelta(seconds=getattr(settings, 'CLIENT_EMAIL_RETRIES_WAIT', 5400))  # retry every 1.5h
                if self.retries >= getattr(settings, 'CLIENT_EMAIL_RETRIES', 10):  # 10 retries * 1.5h = 15h
                    self.error = True
                # Save all
                self.save()
                if not silent:
                    raise

            if connection:
                email = EM(self.subject, self.body, self.efrom, [self.eto], connection=connection)
                for at in self.attachments.all():
                    with open(at.path) as f:
                        email.attach(at.filename, f.read(), at.mime)

                # send list emails
                retries = 1
                while retries+1:
                    try:
                        if connection.send_messages([email]):
                            # We are done
                            self.sent = True
                            self.sending = False
                            break
                    except ssl.SSLError as e:
                        error = "SSLError: {}\n".format(e)
                        self.warning(error)
                        self.log += error
                    except smtplib.SMTPServerDisconnected as e:
                        error = "SMTPServerDisconnected: {}\n".format(e)
                        self.warning(error)
                        self.log += error
                    except smtplib.SMTPException as e:
                        error = "SMTPException: {}\n".format(e)
                        self.warning(error)
                        self.log += error
                    finally:
                        # One chance less
                        retries -= 1
                        # Check if this is the last try
                        if not retries:
                            # We will not retry anymore
                            self.sending = False
                            # We make lower this email's priority
                            self.priority += 1
                            # Set new retry
                            self.retries += 1
                            self.next_retry = timezone.now() + timezone.timedelta(seconds=getattr(settings, 'CLIENT_EMAIL_RETRIES_WAIT', 5400))  # retry every 1.5h
                            if self.retries >= getattr(settings, 'CLIENT_EMAIL_RETRIES', 10):  # 10 retries * 1.5h = 15h
                                self.error = True
                        # Save the email
                        self.save()
                        # Disconnect
                        connection.close()
                        # Connect
                        connection = self.connect(legacy)


class EmailAttachment(CodenerixModel):
    email = models.ForeignKey(EmailMessage, blank=False, null=False, related_name="attachments")
    filename = models.CharField(_('Filename'), max_length=256, blank=False, null=False)
    mime = models.CharField(_('Mimetype'), max_length=256, blank=False, null=False)
    path = models.FileField(_('Path'), blank=False, null=False)

    def __fields__(self, info):
        fields = []
        fields.append(('email', _('Email'), 100))
        fields.append(('filename', _('Filename'), 100))
        fields.append(('mime', _('Mimetype'), 100))
        fields.append(('path', _('Path'), 100))
        return fields


class EmailTemplate(CodenerixModel):
    cid = models.CharField(_('CID'), unique=True, max_length=30, blank=False, null=False)
    efrom = models.TextField(_('From'), blank=True, null=False)

    def __fields__(self, info):
        fields = []
        fields.append(('pk', _('PK'), 100))
        fields.append(('cid', _('CID'), 100))
        fields.append(('efrom', _('From'), 100))
        return fields

    def __str__(self):
        return "{}:{}".format(self.cid, self.pk)

    def __unicode__(self):
        return self.__str__()

    @staticmethod
    def get(cid=None, context={}, pk=None, lang=None):
        '''
        Usages:
            EmailTemplate.get('PACO', ctx) => EmailMessage(): le falta el eto
            > cid: PACO
            EmailTemplate.get(pk='PACO', context=ctx) => EmailMessage(): le falta el eto
            > pk: PACO    (we don't have CID)
        '''
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
        e.subject = Template(getattr(self, lang).subject).render(Context(context))
        e.body = Template(getattr(self, lang).body).render(Context(context))
        e.efrom = Template(self.efrom).render(Context(context))
        return e

    def clean(self):
        if self.cid:
            self.cid = self.cid.upper()
            if len(re.findall(r"[A-Za-z0-9]+", self.cid)) != 1:
                raise ValidationError(_("CID can contains only number and letters with no spaces"))


class GenText(CodenerixModel):  # META: Abstract class
    class Meta(CodenerixModel.Meta):
        abstract = True

    subject = models.TextField(_('Subject'), blank=True, null=False)
    body = WysiwygAngularField(_('Body'), blank=True, null=False)

    def __fields__(self, info):
        fields = []
        fields.append(('subject', _('Subject'), 100))
        fields.append(('body', _('Body'), 100))
        return fields

    def __unicode__(self):
        return u"{}".format(self.subject)

    def __str__(self):
        return self.__unicode__()


MODELS = [
    ("email_template", "EmailTemplate"),
]

for info in MODELS:
    field = info[0]
    model = info[1]
    for lang_code in settings.LANGUAGES_DATABASES:
        query = "class {}Text{}(GenText):\n".format(model, lang_code)
        query += "  {} = models.OneToOneField({}, blank=False, null=False, related_name='{}')\n".format(field, model, lang_code.lower())
        exec(query)
