from .email_test import Command as RealCommand


class Command(RealCommand):
    def handle(self, *args, **options):
        self.stderr.write(
            "WARNING: 'test_email' is DEPRECATED, switch to 'emails_send'"
        )
        return super().handle(*args, **options)
