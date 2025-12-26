"""
Simple development logger for E-commerce backend.

Usage:
    from Utils.logger import logger
    logger.info("User login successful")
    logger.error("Payment failed")
    logger.exception("Unexpected error occurred")
"""

import logging
import sys
from logging import Logger

from utils.logging_filter import UserContextFilter

# Create logger once
_logger: Logger = logging.getLogger("ecommerce")

# Prevent duplicate handlers on uvicorn reload
if not _logger.handlers:
    # Set log level
    _logger.setLevel(logging.DEBUG)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    # Create formatter: timestamp | level | logger | user | message
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | user=%(user)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)

    # Attach handler
    _logger.addHandler(console_handler)

    # Attach user context filter
    _logger.addFilter(UserContextFilter())

    # Prevent propagation to root logger (avoid duplicate logs)
    _logger.propagate = False

# Export the logger instance
logger = _logger
