import sys

if not sys.argv[0].startswith("email"):
    import logging

    logger = logging.getLogger("codenerix")
    logger.warning(
        "WARNING: 'recv_emails' is DEPRECATED, switch to 'emails_recv' instead"
    )

from .emails_recv import *  # type: ignore # noqa
