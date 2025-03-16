"""PID namespace handler."""

import ctypes
import logging
import os

from src.namespace.handlers import NamespaceHandler

CLONE_NEWPID = 0x20000000

logger = logging.getLogger(__name__)


class PidNamespaceHandler(NamespaceHandler):
    """Handler for PID namespace isolation.

    This handler is responsible for creating a new PID namespace
    for the container, allowing processes inside to have their own
    isolated process ID space.
    """

    def __init__(self) -> None:
        """Initialize PID namespace handler."""
        super().__init__()

    def setup(self) -> None:
        """Apply PID namespace isolation.

        This creates a new PID namespace but doesn't fork a new process.
        Instead, it uses unshare() to prepare the current process to spawn
        children in a new PID namespace.

        Note that the current process remains in its original PID namespace,
        but any children it creates after this call will be in the new namespace.

        Returns:
            None
        """
        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        result = libc.unshare(CLONE_NEWPID)
        if result < 0:
            errno = ctypes.get_errno()
            raise OSError(errno, f"unshare failed: {os.strerror(errno)}")
