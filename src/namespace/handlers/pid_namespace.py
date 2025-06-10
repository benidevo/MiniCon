"""PID namespace handler."""

import ctypes
import logging
import os
from typing import Any, Callable

from src.constants import CLONE_NEWPID
from src.namespace.handlers import NamespaceHandler

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
        from src.utils.system import load_libc

        libc = load_libc()

        result = libc.unshare(CLONE_NEWPID)
        if result < 0:
            errno = ctypes.get_errno()
            raise OSError(errno, f"unshare failed: {os.strerror(errno)}")

    def fork_in_new_namespace(self, child_func: Callable[[], Any]) -> int:
        """Fork a process that becomes PID 1 in the new PID namespace.

        Args:
            child_func: Function to call in the container process.

        Returns:
            The PID of the container process in the parent namespace.
        """
        # Single fork - child will be in new PID namespace
        pid = os.fork()
        if pid == 0:
            try:
                exit_code = child_func()
                os._exit(exit_code if isinstance(exit_code, int) else 0)
            except Exception as e:
                logger.error(f"Error in container process: {e}")
                os._exit(1)
        else:
            self._child_pid = pid
            return pid

    def fork_in_new_namespace_sync(
        self, child_func: Callable[[], Any], read_fd: int, write_fd: int
    ) -> int:
        """Fork a process that becomes PID 1 with synchronization.

        Uses a simpler single fork with synchronization to avoid complexity
        of tracking the double fork process hierarchy.

        Args:
            child_func: Function to call in the container process.
            read_fd: File descriptor for child to read synchronization signal.
            write_fd: File descriptor for parent to write synchronization signal.

        Returns:
            The PID of the container process in the parent namespace.
        """
        pid = os.fork()
        if pid == 0:
            try:
                # Child process: wait for parent signal
                os.close(write_fd)  # Close write end in child
                os.read(read_fd, 2)  # Wait for "go" signal
                os.close(read_fd)  # Close read end after signal

                exit_code = child_func()
                os._exit(exit_code if isinstance(exit_code, int) else 0)
            except Exception as e:
                logger.error(f"Error in container process: {e}")
                os._exit(1)
        else:
            # Parent: close read end and track the container process
            os.close(read_fd)  # Close read end in parent
            self._child_pid = pid
            return pid
