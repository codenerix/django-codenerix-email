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


from django.core.management.base import BaseCommand
from django.conf import settings

from codenerix.lib.debugger import Debugger
from codenerix_email.models import EmailMessage


class Command(BaseCommand, Debugger):

    # Show this when the user types help
    help = "Try to send all emails in the queue"
    
    def handle(self, *args, **options):
        
        # Autoconfigure Debugger
        self.set_name("CODENERIX-EMAIL")
        self.set_debug()
        
        # Get a lock system???
        
        # Get a bunch of emails in the queue
        connection = None
        emails = EmailMessage.objects.filter(sent=False, sending=False).order_by('priority', 'created')[0:getattr(settings, 'CLIENT_EMAIL_BUCKETS', 1000)]
        # While we have emails
        while emails:
            
            list_emails = [x.pk for x in emails]
            # Set sending
            EmailMessage.objects.filter(pk__in=list_emails).update(sending=True)
            
            # For each email
            for email in emails:
                
                # Check if we have connection
                if not connection:
                    connection = email.connect()
                
                # Send the email
                email.send(connection)
            
            # Mark as done
            if getattr(settings, 'CLIENT_EMAIL_HISTORY', True):
                EmailMessage.objects.filter(pk__in=list_emails).update(sent=True, sending=False)
            else:
                EmailMessage.objects.filter(pk__in=list_emails).delete()
            
            # Once done, get more to send
            emails = EmailMessage.objects.filter(sent=False, sending=False).order_by('priority', 'created')[0:getattr(settings, 'CLIENT_EMAIL_BUCKETS', 1000)]
