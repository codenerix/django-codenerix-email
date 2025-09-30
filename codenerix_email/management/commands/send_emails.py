import sys

if not sys.argv[0].startswith("email"):
    import logging

    logger = logging.getLogger("codenerix")
    logger.warning(
        "WARNING: 'send_emails' is DEPRECATED, switch to 'emails_send' instead"
    )

from .emails_send import *  # type: ignore # noqa
