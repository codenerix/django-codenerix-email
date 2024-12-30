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


from django.core.management.base import BaseCommand
from django.conf import settings

from codenerix_lib.debugger import Debugger
from codenerix_email.models import EmailMessage
from codenerix_email import __version__


class Command(BaseCommand, Debugger):

    # Show this when the user types help
    help = "Test"

    def handle(self, *args, **options):

        # Autoconfigure Debugger
        self.set_name("CODENERIX-EMAIL")
        self.set_debug()

        message = """Hello,

this email has been sent using Django Codenerix Email.

Best regards, Codenerix Team

--
Django Codenerix Email v{}""".format(
            __version__
        )

        for name, email in settings.ADMINS:
            email_message = EmailMessage()
            email_message.efrom = settings.DEFAULT_FROM_EMAIL
            email_message.eto = email
            email_message.subject = "[Codenerix Email] Test"
            email_message.body = message
            email_message.save()
            email_message.send(legacy=False, silent=False)
