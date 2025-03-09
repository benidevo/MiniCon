"""Mount namespace handler."""

import ctypes
import logging
import os
from typing import Any, Callable, Optional

from src.namespace.handlers import NamespaceHandler

CLONE_NEWNS = 0x00020000

logger = logging.getLogger(__name__)


class MountNamespaceHandler(NamespaceHandler):
    """Provides a specific implementation for handling Mount namespaces.

    This class is designed to manage the setup of a Mount namespace for a container.
    """

    def __init__(self) -> None:
        """Initialize Mount namespace handler."""
        self._child_pid: Optional[int] = None
        self._root_fs: Optional[str] = None

    def setup(self) -> None:
        """Sets up a Mount namespace for a container.

        This method should be called after the container process has been
        created and before it has been started.
        """
        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        result = libc.unshare(CLONE_NEWNS)
        if result < 0:
            errno = ctypes.get_errno()
            raise OSError(errno, f"unshare failed: {os.strerror(errno)}")

        logger.info("Mount namespace setup completed.")

    def fork_in_new_namespace(self, child_func: Callable[[], Any]) -> int:
        """Fork a process in the new Mount namespace.

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

    def set_root_fs(self, root_fs_path: str) -> None:
        """Set the root filesystem for the container.

        Args:
            root_fs_path: The path to the root filesystem.
        """
        self._root_fs = root_fs_path

    def apply_mount_isolation(self) -> None:
        """Apply mount isolation by changing root and mounting proc.

        This should be called in the child process after fork.
        """
        if not self._root_fs:
            raise ValueError("Root filesystem not set.")

        os.system("mount --make-private /")

        os.chroot(self._root_fs)
        os.chdir("/")

        proc_path = "/proc"
        if not os.path.exists(proc_path):
            os.mkdir(proc_path)

        os.system(f"mount -t proc proc {proc_path}")

        logger.info(f"Mount isolation applied to {self._root_fs}, proc mounted.")

    @property
    def child_pid(self) -> Optional[int]:
        """Get the PID of the child process in the parent namespace.

        Returns:
            The PID of the child or None if not created.
        """
        return self._child_pid

    @property
    def root_fs(self) -> Optional[str]:
        """Get the root filesystem of the container.

        Returns:
            The root filesystem path or None if not set.
        """
        return self._root_fs
