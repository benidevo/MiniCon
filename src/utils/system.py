"""System utility functions for MiniCon."""

import ctypes
import logging
from typing import Any

from ..constants import LIBC_PATHS

logger = logging.getLogger(__name__)


def load_libc() -> Any:
    """Load libc library with fallback for different architectures.

    Returns:
        ctypes.CDLL: Loaded libc library

    Raises:
        OSError: If no libc library could be loaded
    """
    for path in LIBC_PATHS:
        try:
            libc = ctypes.CDLL(path, use_errno=True)
            logger.debug(f"Successfully loaded libc from {path}")
            return libc
        except OSError:
            logger.debug(f"Failed to load libc from {path}")
            continue

    raise OSError(f"Could not load libc library from any of: {LIBC_PATHS}")
