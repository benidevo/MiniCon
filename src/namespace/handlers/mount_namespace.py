"""Mount namespace handler."""

import ctypes
import logging
import os
from typing import Optional

from src.constants import CLONE_NEWNS
from src.namespace.handlers import NamespaceHandler
from src.utils.security import SecurityError, safe_make_mount_private, safe_mount_proc

logger = logging.getLogger(__name__)


class MountNamespaceHandler(NamespaceHandler):
    """Provides a specific implementation for handling Mount namespaces.

    This class is designed to manage the setup of a Mount namespace for a container.
    """

    def __init__(self) -> None:
        """Initialize Mount namespace handler."""
        super().__init__()
        self._root_fs: Optional[str] = None

    def setup(self) -> None:
        """Sets up a Mount namespace for a container.

        This method should be called after the container process has been
        created and before it has been started.
        """
        from src.utils.system import load_libc

        libc = load_libc()

        result = libc.unshare(CLONE_NEWNS)
        if result < 0:
            errno = ctypes.get_errno()
            raise OSError(errno, f"unshare failed: {os.strerror(errno)}")

        logger.info("Mount namespace setup completed.")

    def set_root_fs(self, root_fs_path: str) -> None:
        """Set the root filesystem for the container.

        Args:
            root_fs_path: The path to the root filesystem.
        """
        self._root_fs = root_fs_path

    def apply_mount_isolation(self) -> None:
        """Apply mount isolation by changing root and mounting proc.

        This should be called in the child process after fork.

        Raises:
            ValueError: If root filesystem not set.
            SecurityError: If security validation fails.
        """
        if not self._root_fs:
            raise ValueError("Root filesystem not set.")

        try:
            # Make all mounts private to prevent propagation
            safe_make_mount_private()

            # Create minimal proc, sys, dev in container
            self._setup_essential_mounts()

            # Change root to container filesystem
            os.chroot(self._root_fs)
            os.chdir("/")

            # Mount essential filesystems inside container
            self._mount_container_essentials()

            logger.info(
                f"Mount isolation applied to {self._root_fs}, essential mounts created."
            )
        except SecurityError as e:
            logger.error(f"Security error during mount isolation: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to apply mount isolation: {e}")
            raise

    def _setup_essential_mounts(self) -> None:
        """Setup essential mount points in container root."""
        if not self._root_fs:
            return

        essential_dirs = ["/proc", "/sys", "/dev", "/tmp"]
        for dir_path in essential_dirs:
            container_path = os.path.join(self._root_fs, dir_path.lstrip("/"))
            os.makedirs(container_path, exist_ok=True)

    def _mount_container_essentials(self) -> None:
        """Mount essential filesystems inside container."""
        try:
            # Mount /proc for process information
            from src.constants import PROC_PATH

            if os.path.exists(PROC_PATH):
                try:
                    safe_mount_proc(PROC_PATH)
                    logger.info("Successfully mounted /proc")
                except Exception as proc_e:
                    logger.warning(f"Could not mount /proc: {proc_e}")
                    # Continue without /proc - not critical for basic operations

            logger.info("Essential container filesystem setup completed.")
        except Exception as e:
            logger.warning(f"Failed to mount some essential filesystems: {e}")

    @property
    def root_fs(self) -> Optional[str]:
        """Get the root filesystem of the container.

        Returns:
            The root filesystem path or None if not set.
        """
        return self._root_fs
