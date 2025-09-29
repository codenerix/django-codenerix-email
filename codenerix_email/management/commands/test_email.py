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

import json

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

from codenerix_lib.debugger import Debugger
from codenerix_email.models import EmailMessage, EmailTemplate
from codenerix_email import __version__
from django.core.management import CommandError


class Command(BaseCommand, Debugger):
    # Show this when the user types help
    help = "Test"

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            type=str,
            help="Email",
            default=None,
        )
        parser.add_argument(
            "--template",
            type=str,
            help="Template CID",
            default=None,
        )
        parser.add_argument(
            "--context",
            type=str,
            help="Context as JSON",
            default="{}",
        )
        parser.add_argument(
            "--language",
            type=str,
            help="Language",
            default=None,
        )
        parser.add_argument(
            "--stdout",
            action="store_true",
            help="Print to stdout",
            default=False,
        )

    def handle(self, *args, **options):
        # Autoconfigure Debugger
        self.set_name("CODENERIX-EMAIL")
        self.set_debug()

        # Get arguments
        email = options["email"]
        template = options["template"]
        context_str = options["context"]
        language = options["language"]
        stdout = options["stdout"]

        # Read context
        try:
            context = json.loads(context_str)
        except json.JSONDecodeError:
            raise CommandError(
                "Context is not a valid JSON string: {}".format(context_str)
            )

        # If no template is provided, use the default one
        if template is None:
            # Get the default template
            message = """Hello,

This email has been sent using Django Codenerix Email.

Best regards, Codenerix Team

--
Django Codenerix Email v{}
""".format(
                __version__
            )

            def email_message_factory(context, language):
                email_message = EmailMessage()
                email_message.subject = "[Codenerix Email] Test"
                email_message.body = message
                return email_message

        else:
            # Get the template
            try:
                template = EmailTemplate.objects.get(cid=template)
            except EmailTemplate.DoesNotExist:
                raise CommandError(
                    "Template with CID {} does not exist.".format(template)
                )

            # Render the template
            def email_message_factory(context, language):
                return template.get_email(context, language)

        # If no email is provided, send to all admins
        if email is None:
            # Send email to all admins
            for name, email in settings.ADMINS:
                email_message = email_message_factory(context, language)
                email_message.efrom = settings.DEFAULT_FROM_EMAIL
                email_message.eto = email

                # Prepare message ID info
                ecid = email_message.uuid.hex
                edomain = settings.EMAIL_FROM.split("@")[-1]
                ets = int(timezone.now().timestamp())
                email_message.headers = {
                    "Message-ID": f"<{ecid}-{ets}@{edomain}>",
                    "X-Codenerix-Email": "Test",
                }

                if stdout:
                    self.debug(
                        f"Sending email to {name} <{email}> "
                        f"with subject: {email_message.subject}:\n"
                        f"{email_message.body}",
                        color="white",
                    )
                else:
                    email_message.save()
                    email_message.send(legacy=False, silent=False)
        else:
            # Send email to the specified address
            email_message = email_message_factory(context, language)
            email_message.efrom = settings.DEFAULT_FROM_EMAIL
            email_message.eto = email

            # Prepare message ID info
            ecid = email_message.uuid.hex
            edomain = settings.EMAIL_FROM.split("@")[-1]
            ets = int(timezone.now().timestamp())
            email_message.headers = {
                "Message-ID": f"<{ecid}-{ets}@{edomain}>",
                "X-Codenerix-Email": "Test",
            }

            if stdout:
                self.debug(
                    f"Sending email to {name} <{email}> "
                    f"with subject: {email_message.subject}:\n"
                    f"{email_message.body}",
                    color="white",
                )
            else:
                email_message.save()
                email_message.send(legacy=False, silent=False)
