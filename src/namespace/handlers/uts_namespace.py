"""UTS namespace handler."""

import ctypes
import logging
import os
from typing import Optional

from src.namespace.handlers import NamespaceHandler

CLONE_NEWUTS = 0x04000000

logger = logging.getLogger(__name__)


class UtsNamespaceHandler(NamespaceHandler):
    """Provides a specific implementation for handling UTS namespaces.

    This class is designed to manage the setup of a UTS namespace for a container.
    """

    def __init__(self) -> None:
        """Initialize UTS namespace handler."""
        super().__init__()
        self._hostname: Optional[str] = None

    def setup(self) -> None:
        """Apply UTS namespace isolation.

        This creates a new UTS namespace but doesn't fork a new process.
        Instead, it uses unshare() to prepare the current process to spawn
        children in a new UTS namespace.

        Note that the current process remains in its original UTS namespace,
        but any children it creates after this call will be in the new namespace.

        Returns:
            None
        """
        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        result = libc.unshare(CLONE_NEWUTS)
        if result < 0:
            errno = ctypes.get_errno()
            raise OSError(errno, f"unshare failed: {os.strerror(errno)}")

        logger.info("UTS namespace setup completed.")

    def apply_uts_isolation(self) -> None:
        """Apply UTS isolation by changing hostname.

        This should be called in the child process after fork.
        """
        if not self._hostname:
            raise ValueError("Hostname not set.")

        os.system(f"hostname {self._hostname}")

        logger.info(f"UTS isolation applied to {self._hostname}")

    def set_hostname(self, hostname: str) -> None:
        """Set the hostname for the container.

        Args:
            hostname: The hostname to set.

        Returns:
            None
        """
        self._hostname = hostname

    @property
    def hostname(self) -> Optional[str]:
        """Get the hostname for the container.

        Returns:
            The hostname for the container.
        """
        return self._hostname
