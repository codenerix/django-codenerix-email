import sys

if not sys.argv[0].startswith("email"):
    import logging

    logger = logging.getLogger("codenerix")
    logger.warning(
        "WARNING: 'test_email' is DEPRECATED, switch to 'email_test' instead"
    )

from .email_test import *  # type: ignore # noqa
