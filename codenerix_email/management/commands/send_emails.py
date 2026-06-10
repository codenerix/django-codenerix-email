from .emails_send import Command as RealCommand


class Command(RealCommand):
    def handle(self, *args, **options):
        self.stderr.write(
            "WARNING: 'send_emails' is DEPRECATED, switch to 'emails_send'"
        )
        return super().handle(*args, **options)
