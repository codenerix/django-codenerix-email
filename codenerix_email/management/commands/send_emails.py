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

import time

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

from codenerix.lib.debugger import Debugger
from codenerix_email.models import EmailMessage


class Command(BaseCommand, Debugger):

    # Show this when the user types help
    help = "Try to send all emails in the queue"

    def add_arguments(self, parser):

        # Named (optional) arguments
        parser.add_argument('-d',
                            action='store_true',
                            dest='d',
                            default=False,
                            help='Keep the command working forever as a daemon')

        # Named (optional) arguments
        parser.add_argument('--daemon',
                            action='store_true',
                            dest='daemon',
                            default=False,
                            help='Keep the command working forever as a daemon')

        # Named (optional) arguments
        parser.add_argument('-c',
                            action='store_true',
                            dest='c',
                            default=False,
                            help='Clear the sending status to all the Queue')

        # Named (optional) arguments
        parser.add_argument('--clear',
                            action='store_true',
                            dest='clear',
                            default=False,
                            help='Clear the sending status to all the Queue')

    def handle(self, *args, **options):

        # Autoconfigure Debugger
        self.set_name("CODENERIX-EMAIL")
        self.set_debug()

        # Get user configuration
        daemon = bool(options['daemon'] or options['d'])
        clear = bool(options['clear'] or options['c'])
        BUCKET_SIZE = getattr(settings, 'CLIENT_EMAIL_BUCKETS', 10)
        if daemon:
            self.debug("Starting command in DAEMON mode with a queue of {} emails".format(BUCKET_SIZE), color='cyan')
        else:
            self.debug("Starting a queue of {} emails".format(BUCKET_SIZE), color='blue')

        # In if requested set sending status for all the list to False
        if clear:
            EmailMessage.objects.filter(sending=True).update(sending=False)

        # Get a bunch of emails in the queue
        connection = None

        # If daemon mode is requested
        first = True
        while first or daemon:

            # Get a bucket of emails
            emails = EmailMessage.objects.filter(sent=False, sending=False, error=False, next_retry__lte=timezone.now()).order_by('priority', 'next_retry')[0:BUCKET_SIZE+1]

            # Check if there are emails to process
            if emails:

                # Convert to list
                list_emails = [x.pk for x in emails]

                # Set sending status for all the list
                EmailMessage.objects.filter(pk__in=list_emails).update(sending=True)

                # For each email
                for email in emails:
                    self.debug("Sending to {}".format(email.eto), color='white', tail=False)

                    # Check if we have connection
                    if not connection:
                        self.debug(" - Connecting", color='yellow', head=False, tail=False)
                        connection = email.connect()

                    # Send the email
                    try:
                        email.send(connection, debug=False)
                    except Exception as e:
                        email.sending = False
                        error = "Exception: {}\n".format(e)
                        email.log += error
                        email.save()
                        self.error(error)
                    if email.sent:
                        self.debug(" -> SENT", color='green', head=False)
                    else:
                        self.debug(" -> ERROR", color='red', head=False, tail=False)
                        self.debug(" ({} retries left)".format(getattr(settings, 'CLIENT_EMAIL_RETRIES', 10) - email.retries), color='cyan', head=False)

                # Delete all that have been sent
                if not getattr(settings, 'CLIENT_EMAIL_HISTORY', True):
                    EmailMessage.objects.filter(pk__in=list_emails, sent=True).delete()

            elif daemon:

                # Sleep for a while
                try:
                    time.sleep(10)
                except KeyboardInterrupt:
                    self.debug("Exited by user request!", color='green')
                    break

            else:
                # No emails to send
                self.debug("No emails to be sent at this moment in the queue!", color='green')

            # This was the first time
            first = False
