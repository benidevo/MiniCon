"""PID namespace handler."""

import ctypes
import logging
import os
from typing import Any, Callable, Optional

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
        self._child_pid: Optional[int] = None

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

    def fork_in_new_namespace(self, child_func: Callable[[], Any]) -> int:
        """Fork a process in the new PID namespace.

        This should be called after setup() by the orchestrator.
        The child process will be PID 1 in the new namespace.

        Args:
            child_func: Function to call in the child process.

        Returns:
            The PID (in the parent namespace) of the forked child.
        """
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

    @property
    def child_pid(self) -> Optional[int]:
        """Get the PID of the child process in the parent namespace.

        Returns:
            The PID of the child or None if not created.
        """
        return self._child_pid
