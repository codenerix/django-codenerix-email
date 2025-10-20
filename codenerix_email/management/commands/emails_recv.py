import re
import codecs
from textwrap import dedent
from argparse import RawTextHelpFormatter

import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from zoneinfo import ZoneInfo

from email import message_from_bytes
from email.header import decode_header
from email.message import Message
from email.parser import HeaderParser
from typing import Optional

from codenerix_email.models import (
    EmailMessage,
    EmailReceived,
    BOUNCE_SOFT,
    BOUNCE_HARD,
)


# Silence DEBUG logs from imapclient
logging.getLogger("imapclient").setLevel(logging.WARNING)

import imaplib  # noqa: E402
from imapclient import IMAPClient  # noqa: E402
from imapclient.exceptions import LoginError  # noqa: E402


class Command(BaseCommand):
    help = "Fetches new emails from the configured IMAP account."

    def create_parser(self, prog_name, subcommand, **kwargs):
        """
        Create and return the ArgumentParser instance for this command.
        We are overriding this to use the RawTextHelpFormatter.
        """
        parser = super().create_parser(prog_name, subcommand, **kwargs)
        parser.formatter_class = RawTextHelpFormatter
        return parser

    def add_arguments(self, parser):
        parser.epilog = dedent(
            r"""
            This command connects to the configured IMAP server, fetches new
            emails, and saves them as ReceivedEmail objects in the database.

            By default, it processes only unseen emails. You can use the
            --all option to process all emails in the inbox.

            You can filter by specific IMAP ID, Message-ID, or Tracking ID
            using the respective options.

            The --rewrite option allows overwriting existing received emails
            with the same Message-ID.

            Examples:
                # Fetch unseen emails
                python manage.py emails_recv

                # Fetch all emails
                python manage.py emails_recv --all

                # Fetch email by specific IMAP ID
                python manage.py emails_recv --imap-id 123

                # Fetch email by specific Message-ID
                python manage.py emails_recv --message-id "<...>"

                # Fetch email by specific Tracking ID
                python manage.py emails_recv --tracking-id "uuid"

            Make sure to configure the IMAP settings in your Django settings:
                IMAP_EMAIL_HOST = "imap.example.com"
                IMAP_EMAIL_PORT = 993
                IMAP_EMAIL_USER = "your_username"
                IMAP_EMAIL_PASSWORD = "your_password"
                IMAP_EMAIL_SSL = True  #  (default: True)
                IMAP_EMAIL_INBOX_FOLDER = "INBOX"  #  (default: "INBOX")
                IMAP_EMAIL_SELECTOR = "UNSEEN"  #  (default: "UNSEEN")
                IMAP_EMAIL_SEEN = True  #  (default: True)
                IMAP_EMAIL_DELETE = False  #  (default: False)
                IMAP_EMAIL_FILTERS = {
                    "SUBJECT": [r".*"],
                    "FROM": [r".*"],
                    "MESSAGE-ID": [r".*"],
                    "TO": [
                        r"^bounce@becas\.com",
                        r"^bounces@becas\.com",
                        r"^no-reply@becas\.com",
                        r"^hola@becas\.com",
                        r"^tuasesor@becas\.com",
                        r"^[a-zA-Z0-9._%+-]+@becas\.com",  # *@becas.com
                    ],
                    "BODY_PLAIN": [r".*"],
                    "BODY_HTML": [r".*"],
                    "HEADER": [("X-Custom-Header", r".*")],
                    "BOUNCE_TYPE": ["hard", "soft"],
                    "BOUNCE_REASON": [r".*"],
                    "TRACKING_ID": True,
                }

            Filters are applied using AND logic across different fields and
            OR logic within the same field.

            The filters works as follows:
                - SUBJECT, FROM, MESSAGE-ID, TO, BODY_PLAIN, BODY_HTML:
                  regex match (case-insensitive) against the respective field.
                - HEADER: tuple of (header name, regex) to match specific headers.
                - BOUNCE_TYPE: "hard" or "soft" to filter by bounce type.
                - BOUNCE_REASON: regex to match the bounce reason.
                - TRACKING_ID: if True, only process emails with a tracking ID.

            If IMAP_EMAIL_FILTERS is not set, all emails are processed.

            Note: This command marks processed emails as read (Seen) to avoid
            reprocessing them in future runs.
"""  # noqa: E501
        )

        # Named (optional) arguments
        parser.add_argument(
            "--silent",
            action="store_true",
            dest="silent",
            default=False,
            help="Enable silent mode",
        )

        parser.add_argument(
            "--tracking-id", type=str, help="Tracking ID to filter"
        )
        parser.add_argument("--imap-id", type=str, help="IMAP ID to filter")
        parser.add_argument(
            "--message-id", type=str, help="Message-ID to filter"
        )
        parser.add_argument(
            "--all", action="store_true", help="Process all emails"
        )
        parser.add_argument(
            "--rewrite", action="store_true", help="Rewrite existing"
        )

    def validate_encoding(self, encoding: str | None) -> str:
        """
        Validates and returns a safe encoding name.
        """
        # If an encoding is specified, verify it's valid
        if encoding:
            try:
                # Attempt to look up the encoding to see if it's known
                codecs.lookup(encoding)
            except LookupError:
                # If the lookup fails, the encoding is unknown
                # Fall back to a safe default like 'latin-1'
                encoding = "latin-1"
        else:
            # If no encoding is specified, use a default
            encoding = "utf-8"
        return encoding

    def handle(self, *args, **options):
        # Get configuration
        self.silent = options["silent"]
        self.verbose = not self.silent
        self.imap_id = options.get("imap_id")
        self.message_id = options.get("message_id")
        self.tracking_id = options.get("tracking_id")
        self.rewrite = options.get("rewrite", False)
        self.process_all = options.get("all", False)

        # Show header
        if self.verbose:
            self.stdout.write(
                self.style.SUCCESS("Starting IMAP email synchronization...")
            )

        # Get configuration from settings
        host = getattr(settings, "IMAP_EMAIL_HOST", None)
        port = getattr(settings, "IMAP_EMAIL_PORT", 993)
        user = getattr(settings, "IMAP_EMAIL_USER", None)
        password = getattr(settings, "IMAP_EMAIL_PASSWORD", None)
        ssl = getattr(settings, "IMAP_EMAIL_SSL", True)
        folder = getattr(settings, "IMAP_EMAIL_INBOX_FOLDER", "INBOX")

        # Verify that IMAP settings are configured
        if host is not None and port:
            # Validate configuration
            if user is None or password is None:
                if self.silent:
                    return
                else:
                    raise CommandError(
                        "IMAP user or password not configured. Please set "
                        "IMAP_EMAIL_USER and IMAP_EMAIL_PASSWORD in settings."
                    )

            try:
                # Connect to the IMAP server
                server = IMAPClient(host, port=port, ssl=ssl)
            except Exception as e:
                raise CommandError(
                    f"Failed to connect to IMAP server ("
                    f"{host=}, "
                    f"{port=}, "
                    f"ssl={ssl and 'yes' or 'no'}"
                    f"): {e}"
                ) from e

            try:
                # Login and select the inbox
                try:
                    server.login(user, password)
                except LoginError as e:
                    raise CommandError(
                        f"Failed to login to IMAP server with {user=}: {e}"
                    ) from e

                if folder:
                    try:
                        server.select_folder(folder, readonly=False)
                    except imaplib.IMAP4.error:
                        raise CommandError(f"Failed to select inbox {folder=}")

                # Process emails
                (created_count, overwritten_count) = self.process(server)
                count = created_count + overwritten_count

                # Show summary
                if self.verbose:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Successfully synchronized {count} emails "
                            f"(new: {created_count}, "
                            f"overwritten: {overwritten_count})"
                        )
                    )

            except Exception as e:
                raise
                self.stderr.write(
                    self.style.ERROR(
                        f"An error occurred during synchronization: {e}"
                    )
                )

            finally:
                # Logout from the server
                try:
                    server.logout()
                except Exception:
                    pass

        elif self.verbose:
            raise CommandError(
                "IMAP settings not configured. Please set IMAP_EMAIL_HOST "
                "and IMAP_EMAIL_PORT in settings."
            )

    def process(self, server):
        """
        Connects to the IMAP server and fetches new emails,
        saving them as ReceivedEmail objects.
        """

        # Processed emails count
        created_count = 0
        overwrite_count = 0

        # Look up for emails
        if self.imap_id:
            # Search by specific IMAP ID
            try:
                imap_id = int(self.imap_id)
            except ValueError:
                raise CommandError(
                    f"Invalid IMAP ID '{self.imap_id}'. Must be an integer."
                )
            messages_ids = [imap_id]
            if self.verbose:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Processing email with IMAP ID {self.imap_id}."
                    )
                )

        elif self.message_id:
            # Search by specific Message-ID
            messages_ids = server.search(
                ["HEADER", "Message-ID", self.message_id]
            )
            if self.verbose:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Found {len(messages_ids)} email(s) with "
                        f"Message-ID {self.message_id}."
                    )
                )

        elif self.process_all:
            # Process all emails
            messages_ids = server.search(["ALL"])
            if self.verbose:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Found {len(messages_ids)} email(s) to process."
                    )
                )

        else:
            # Search by UNSEEN
            messages_ids = server.search(
                [getattr(settings, "IMAP_EMAIL_SELECTOR", "UNSEEN")]
            )
            if self.verbose:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Found {len(messages_ids)} new email(s) to process."
                    )
                )

        # If there are new messages, fetch and process them
        if messages_ids:
            # Fetch the full message and internal date
            fetched_data = server.fetch(
                messages_ids, ["BODY.PEEK[]", "INTERNALDATE"]
            )

            # Get the envelope (metadata) and the full body
            # Use IMAP IDs so identifiers do not change between sessions
            for imap_id, message_data in fetched_data.items():
                # Filter out by IMAP ID if specified
                if self.imap_id and str(imap_id) != self.imap_id:
                    continue

                # Get the raw email and internal date
                raw_email = message_data[b"BODY[]"]
                internal_date_naive = message_data[b"INTERNALDATE"]
                internal_date = internal_date_naive.replace(
                    tzinfo=ZoneInfo(settings.TIME_ZONE)
                )

                # Parse the email
                msg = message_from_bytes(raw_email)

                # Extract subject
                subject, encoding = decode_header(msg["Subject"])[0]

                # Decode subject if it's bytes
                if isinstance(subject, bytes):
                    charset = self.validate_encoding(encoding)
                    subject = subject.decode(charset, errors="ignore")

                # Extract other headers
                efrom = msg.get("From")
                eto = msg.get("To")
                eid = msg.get("Message-ID")
                ecc = msg.get("Cc")
                ebc = msg.get("Bcc")

                # If we can't get a Message-ID, use the IMAP ID as fallback
                # to avoid duplicates
                if not eid:
                    eid = f"<imapid-{imap_id}@{settings.IMAP_EMAIL_HOST}>"

                # Avoid processing duplicates
                email_received = EmailReceived.objects.filter(eid=eid).first()
                if self.rewrite or not email_received:
                    # Process multipart emails
                    body_plain = ""
                    body_html = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type == "text/plain" and not body_plain:
                                charset = self.validate_encoding(
                                    part.get_content_charset()
                                )
                                body_plain = part.get_payload(
                                    decode=True
                                ).decode(charset, errors="ignore")
                            elif content_type == "text/html" and not body_html:
                                charset = self.validate_encoding(
                                    part.get_content_charset()
                                )
                                body_html = part.get_payload(
                                    decode=True
                                ).decode(charset, errors="ignore")
                    else:
                        charset = self.validate_encoding(
                            msg.get_content_charset()
                        )
                        body_plain = msg.get_payload(decode=True).decode(
                            charset, errors="ignore"
                        )

                    # Logic to associate replies/bounces with sent emails
                    try:
                        email_message = None

                        # Locate the tracking ID
                        tracking_id = self.find_tracking_id(msg)

                        # Filter out by tracking ID if specified
                        if (
                            self.tracking_id
                            and tracking_id != self.tracking_id
                        ):
                            continue

                        # If found, try to link to the sent email
                        if tracking_id:
                            try:
                                email_message = EmailMessage.objects.get(
                                    uuid=tracking_id
                                )
                            except EmailMessage.DoesNotExist:
                                email_message = None
                                if self.verbose:
                                    self.stdout.write(
                                        self.style.WARNING(
                                            f"Tracking ID {tracking_id} found "
                                            f"for IMAP ID {imap_id} but no "
                                            "matching sent email."
                                        )
                                    )

                    except Exception as e:
                        raise CommandError(
                            "Error while linking email with IMAP ID "
                            f"{imap_id} to sent email: {e}"
                        ) from e

                    # Heuristic keywords commonly found in bounce messages
                    (bounce_type, bounce_reason) = self.analyze_bounce(msg)

                    # Extract all headers into a dictionary
                    headers = {}
                    for header, value in msg.items():
                        decoded_value, encoding = decode_header(value)[0]
                        charset = self.validate_encoding(encoding)
                        if isinstance(decoded_value, bytes):
                            decoded_value = decoded_value.decode(
                                charset, errors="ignore"
                            )
                        headers[header] = decoded_value

                    # Let emails pass based on filtering system
                    (filter_passed, filter_reason) = self.filter_pass(
                        subject,
                        efrom,
                        eto,
                        ecc,
                        ebc,
                        eid,
                        body_plain,
                        body_html,
                        headers,
                        bounce_type,
                        bounce_reason,
                        tracking_id,
                    )
                    if not filter_passed:
                        if self.verbose:
                            self.stdout.write(
                                self.style.NOTICE(
                                    f"Skipping email with IMAP ID: {imap_id} "
                                    f"(FILTER: {filter_reason})"
                                )
                            )

                        if getattr(settings, "IMAP_EMAIL_DELETE", False):
                            # Delete the message from the server
                            server.delete_messages(imap_id)
                            server.expunge()
                            if self.verbose:
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        "Deleted email with "
                                        f"IMAP ID: {imap_id}"
                                    )
                                )

                        elif getattr(settings, "IMAP_EMAIL_SEEN", True):
                            # Mark the message as read to avoid reprocessing
                            server.add_flags(imap_id, [b"\\Seen"])

                        continue

                    # Create EmailReceived object if doesn't exist
                    if not email_received:
                        overwriting = False
                        email_received = EmailReceived()
                    else:
                        overwriting = True

                    # Populate fields
                    email_received.imap_id = imap_id
                    email_received.eid = eid
                    email_received.efrom = efrom
                    email_received.eto = eto
                    email_received.subject = subject
                    email_received.headers = headers
                    email_received.body_text = body_plain
                    email_received.body_html = body_html
                    email_received.date_received = internal_date
                    email_received.email = email_message
                    email_received.bounce_type = bounce_type
                    email_received.bounce_reason = bounce_reason

                    # Save the received email
                    email_received.save()

                    # Recalculate the email status if linked to a sent email
                    if email_message:
                        email_message.recalculate_bounces()

                    # Count created or overwritten
                    if overwriting:
                        overwrite_count += 1
                        verb = "Overwritten"
                    else:
                        created_count += 1
                        verb = "Created"

                    # Show info about the processed email
                    if self.verbose:
                        if overwriting:
                            style = self.style.MIGRATE_HEADING
                        else:
                            style = self.style.WARNING
                        msg = (
                            f"{verb} email with IMAP ID: "
                            f"{imap_id} (link={tracking_id})"
                        )
                        if bounce_type:
                            bounce_type_str = (
                                bounce_type == BOUNCE_HARD and "Hard" or "Soft"
                            )
                            bounce_reason_str = bounce_reason or "Unknown"
                            self.stdout.write(
                                style(
                                    f"{msg} "
                                    f"[{bounce_type_str} bounce, "
                                    f"reason={bounce_reason_str}]"
                                )
                            )
                        else:
                            if overwriting:
                                style = self.style.MIGRATE_HEADING
                            else:
                                style = self.style.SUCCESS
                            self.stdout.write(style(msg))

                else:
                    if self.verbose:
                        self.stdout.write(
                            self.style.HTTP_INFO(
                                f"Skipping email with IMAP ID: {imap_id} (DUP)"
                            )
                        )

                if getattr(settings, "IMAP_EMAIL_DELETE", False):
                    # Delete the message from the server
                    server.delete_messages(imap_id)
                    server.expunge()
                    if self.verbose:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Deleted email with IMAP ID: {imap_id}"
                            )
                        )
                elif getattr(settings, "IMAP_EMAIL_SEEN", True):
                    # Mark the message as read otherwise (avoids reprocessing)
                    server.add_flags(imap_id, [b"\\Seen"])

        return (created_count, overwrite_count)

    def find_tracking_id(self, msg: Message) -> str | None:
        """
        Searches for the X-Codenerix-Tracking-ID robustly in an email.

        It performs the search in three steps:
        1. In the main headers of the email.
        2. In the attached parts that are a complete email (message/rfc822).
        3. As a last resort, searches the text in the body of the message.
        """

        # Method 1: Search in main headers (for direct replies)
        tracking_id = msg.get("X-Codenerix-Tracking-ID", None)

        # Method 2: Search in attached parts (for bounces and forwards)
        if not tracking_id:
            # Not found directly in headers
            # Search in attached parts (for bounces and forwards)
            if msg.is_multipart():
                # Iterate through parts
                for part in msg.walk():
                    # Get the content type of the part
                    content_type = part.get_content_type()

                    # We look for an attachment that is itself an email
                    if content_type == "message/rfc822":
                        # The payload of this part is the original email
                        # The payload is a list of messages, take the first one
                        original_msg_payload = part.get_payload()
                        if (
                            isinstance(original_msg_payload, list)
                            and original_msg_payload
                        ):
                            original_msg = original_msg_payload[0]
                            if isinstance(original_msg, Message):
                                tracking_id = original_msg.get(
                                    "X-Codenerix-Tracking-ID"
                                )

                    elif content_type == "text/rfc822-headers":
                        # The payload is the raw headers of the original email
                        headers_payload = part.get_payload(decode=True)
                        if isinstance(headers_payload, bytes):
                            # Decode using the specified charset
                            charset = self.validate_encoding(
                                part.get_content_charset()
                            )
                            headers_text = headers_payload.decode(
                                charset, errors="ignore"
                            )

                            # Parse headers text into a Message object
                            headers_msg = HeaderParser().parsestr(headers_text)
                            tracking_id = headers_msg.get(
                                "X-Codenerix-Tracking-ID"
                            )

            # Method 3: Search in the body text (fallback)
            if not tracking_id:
                # The original email might be quoted as plain text.
                body_text = ""
                if msg.is_multipart():
                    # Concatenate all text/plain parts
                    for part in msg.walk():
                        # We only want text/plain parts
                        if part.get_content_type() == "text/plain":
                            # Get the decoded payload
                            payload = part.get_payload(decode=True)
                            if isinstance(payload, bytes):
                                # Decode using the specified charset
                                charset = self.validate_encoding(
                                    part.get_content_charset()
                                )
                                body_text += payload.decode(
                                    charset, errors="ignore"
                                )
                else:
                    # Single part email, check if it's text/plain
                    if msg.get_content_type() == "text/plain":
                        # Get the decoded payload
                        payload = msg.get_payload(decode=True)
                        if isinstance(payload, bytes):
                            # Decode using the specified charset
                            charset = self.validate_encoding(
                                msg.get_content_charset()
                            )
                            body_text = payload.decode(
                                charset, errors="ignore"
                            )

                # If we have body text, search for the header using regex
                if body_text:
                    # We use a regex to find the header in the text
                    match = re.search(
                        r"X-Codenerix-Tracking-ID:\s*([a-fA-F0-9\-]{36})",
                        body_text,
                    )

                    if match:
                        # If found, extract the tracking ID
                        tracking_id = match.group(1).strip()

        # Return the found tracking ID if any
        return tracking_id

    def analyze_bounce(
        self, msg: Message
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Analyzes an email to determine if it is a bounce and of what type.

        Returns:
            A tuple (bounce_type, smtp_code).
            - bounce_type: BOUNCE_HARD, BOUNCE_SOFT, or None if not a bounce.
            - bounce_reason: the SMTP status code (e.g., '5.1.1') or None.
        """

        # Initialize
        bounce_type: Optional[str] = None
        bounce_reason: Optional[str] = None

        # Method 1: Look for DSN reports
        if (
            msg.get_content_type() == "multipart/report"
            and msg.get_param("report-type") == "delivery-status"
        ):
            # Iterate through parts to find the delivery-status part
            for part in msg.walk():
                # We look for the delivery-status part
                if part.get_content_type() == "message/delivery-status":
                    # The payload is a list of headers
                    payload = part.get_payload()
                    if payload and isinstance(payload, list):
                        # The first part contains the status headers
                        status_headers = payload[0]
                        if isinstance(status_headers, Message):
                            # Extract Action and Status headers
                            action = status_headers.get("Action", "").lower()
                            status_code = status_headers.get("Status", "")

                            # Check if action indicates failure
                            if action == "failed":
                                # Determine Hard/Soft by SMTP code (RFC3463)
                                if status_code.startswith("5."):
                                    # 5.x.x: permanent failure (hard)
                                    bounce_type = BOUNCE_HARD
                                    bounce_reason = status_code
                                    break
                                elif status_code.startswith("4."):
                                    # 4.x.x: temporary failure (soft)
                                    bounce_type = BOUNCE_SOFT
                                    bounce_reason = status_code
                                    break
                                else:
                                    # Unknown status, assume hard bounce
                                    bounce_type = BOUNCE_HARD
                                    bounce_reason = status_code or "Unknown"
                                    break

        # Method 2: Some mail servers include headers indicating a bounce
        if not bounce_type:
            if msg.get("X-Failed-Recipients"):
                # Presence of this header usually indicates a hard bounce
                bounce_type = BOUNCE_HARD
                bounce_reason = "Unknown (X-Failed-Recipients)"

            else:
                # Check for Auto-Submitted header
                if msg.get("Auto-Submitted", "").lower() in (
                    "auto-replied",
                    "auto-generated",
                ):
                    # It could be a bounce, but also an "Out of Office",
                    # so we combine it with a keyword search.
                    subject = msg.get("Subject", "").lower()
                    bounce_keywords = [
                        "undeliverable",
                        "delivery failed",
                        "failure notice",
                    ]

                    # If we find bounce keywords in the subject
                    if any(keyword in subject for keyword in bounce_keywords):
                        # Assume is a hard bounce
                        bounce_type = BOUNCE_HARD
                        bounce_reason = "Unknown (Auto-Submitted + Keyword)"

        # Method 3: keyword search (less reliable)
        if not bounce_type:
            # We look for common bounce keywords in the From or Subject headers
            # We avoid false positives by requiring specific keywords.
            from_header = msg.get("From", "").lower()
            subject_header = msg.get("Subject", "").lower()

            if "mailer-daemon@" in from_header or "postmaster@" in from_header:
                # Common bounce sender addresses
                bounce_type = BOUNCE_HARD
                bounce_reason = "Unknown (From Keyword)"
            else:
                # Check subject for common bounce keywords
                bounce_keywords = [
                    "undelivered",
                    "delivery error",
                    "mail delivery failed",
                ]
                if any(
                    keyword in subject_header for keyword in bounce_keywords
                ):
                    bounce_type = BOUNCE_HARD
                    bounce_reason = "Unknown (Subject Keyword)"

        return (bounce_type, bounce_reason)

    def filter_pass(
        self,
        subject: str,
        efrom: str,
        eto: str,
        ecc: str,
        ebc: str,
        eid: str,
        body_plain: str,
        body_html: str,
        headers: dict,
        bounce_type: Optional[str],
        bounce_reason: Optional[str],
        tracking_id: Optional[str],
    ) -> tuple[bool, str]:
        """
        Applies filtering rules to determine if an email should be processed.

        Returns:
            True if the email should be processed, False otherwise.
        """

        # Get filters from settings
        filters = getattr(settings, "IMAP_EMAIL_FILTERS", None)
        if not filters:
            # No filters defined, allow processing
            return (True, "No filters defined, processing all.")

        # Helper function to apply regex list to a value
        def match_any(value: str, patterns: list) -> bool:
            for pattern in patterns:
                if re.search(pattern, value, re.IGNORECASE):
                    return True  # Match found
            return False  # No matches

        # Apply filters
        for key, patterns in filters.items():
            if key == "SUBJECT" and patterns:
                if not match_any(subject or "", patterns):
                    return (False, f"SUBJECT failed: {subject}")

            elif key == "FROM" and patterns:
                if not match_any(efrom or "", patterns):
                    return (False, f"FROM failed: {efrom}")

            elif key == "TO" and patterns:
                if not any(
                    match_any(targets or "", patterns)
                    for targets in (
                        eto or "",
                        ecc or "",
                        ebc or "",
                    )
                ):
                    # If no direct match, try more robust email extraction
                    # Analize only the email addresses
                    emails = re.split(r"[;,]\s*", eto or "")
                    emails += re.split(r"[;,]\s*", ecc or "")
                    emails += re.split(r"[;,]\s*", ebc or "")

                    # Stay only with the email and strip < and > if present
                    email_only = [
                        e.split()[-1].strip("<>") for e in emails if e
                    ]

                    # Check if any of the emails match
                    if not any(match_any(e, patterns) for e in email_only):
                        return (False, f"TO failed: {eto}")

            elif key == "MESSAGE-ID" and patterns:
                if not match_any(eid or "", patterns):
                    return (False, f"MESSAGE-ID failed: {eid}")

            elif key == "BODY_PLAIN" and patterns:
                if not match_any(body_plain or "", patterns):
                    return (False, f"BODY_PLAIN failed: {body_plain}")

            elif key == "BODY_HTML" and patterns:
                if not match_any(body_html or "", patterns):
                    return (False, f"BODY_HTML failed: {body_html}")

            elif key == "HEADER" and patterns:
                header_matched = False
                for header_name, header_patterns in patterns:
                    header_value = headers.get(header_name, "")
                    if match_any(header_value, header_patterns):
                        header_matched = True
                        break
                if not header_matched:
                    return (False, f"HEADER failed: {headers}")

            elif key == "BOUNCE_TYPE" and patterns:
                if bounce_type not in patterns:
                    return (False, f"BOUNCE_TYPE failed: {bounce_type}")

            elif key == "BOUNCE_REASON" and patterns:
                if not bounce_reason or not match_any(bounce_reason, patterns):
                    return (
                        False,
                        f"BOUNCE_REASON failed: {bounce_reason}",
                    )

            elif key == "TRACKING_ID" and patterns:
                if patterns and not tracking_id:
                    return (False, "TRACKING_ID failed: No tracking ID")

        # If all filters passed, allow processing
        return (True, "All filters passed.")
