"""User namespace handler."""

import ctypes
import logging
import os
from typing import List, Optional, Tuple

from src.namespace.handlers import NamespaceHandler

CLONE_NEWUSER = 0x10000000

logger = logging.getLogger(__name__)


class UserNamespaceHandler(NamespaceHandler):
    """Provides a specific implementation for handling User namespaces.

    This class is designed to manage the setup of a User namespace for a container.
    """

    def __init__(self) -> None:
        """Initialize User namespace handler."""
        super().__init__()
        self._user_id: Optional[int] = None
        self._group_id: Optional[int] = None
        self._uid_mappings: List[Tuple[int, int, int]] = []
        self._gid_mappings: List[Tuple[int, int, int]] = []

    def setup(self) -> None:
        """Apply User namespace isolation.

        This creates a new User namespace but doesn't fork a new process.
        Instead, it uses unshare() to prepare the current process to spawn
        children in a new User namespace.

        Note that the current process remains in its original User namespace,
        but any children it creates after this call will be in the new namespace.

        Returns:
            None
        """
        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        result = libc.unshare(CLONE_NEWUSER)
        if result < 0:
            errno = ctypes.get_errno()
            raise OSError(errno, f"unshare failed: {os.strerror(errno)}")

        logger.info("User namespace setup completed.")

    def set_user(self, user_id: int, group_id: int) -> None:
        """Set the user and group ID for the container.

        Args:
            user_id: The user ID to set.
            group_id: The group ID to set.

        Returns:
            None
        """
        self._user_id = user_id
        self._group_id = group_id

    def add_gid_mapping(self, inside_gid: int, outside_gid: int, count: int) -> None:
        """Add a group ID mapping to be applied when the container is started.

        Args:
            inside_gid: The source group ID to map.
            outside_gid: The target group ID to map to.
            count: The number of IDs to map.
        """
        self._gid_mappings.append((inside_gid, outside_gid, count))

    def add_uid_mapping(self, inside_uid: int, outside_uid: int, count: int) -> None:
        """Add a user ID mapping to be applied when the container is started.

        Args:
            inside_uid: The source user ID to map.
            outside_uid: The target user ID to map to.
            count: The number of IDs to map.
        """
        self._uid_mappings.append((inside_uid, outside_uid, count))

    def apply_user_isolation(self) -> None:
        """Apply UID and GID mappings to the child process.

        This should be called in the parent process after fork and namespace setup.

        Raises:
            ValueError: If UID or GID mappings are not set.
            ValueError: If child process not created yet
        """
        if not self._uid_mappings or not self._gid_mappings:
            raise ValueError("UID or GID mappings not set")

        if not self._child_pid:
            raise ValueError("Child process not created yet")

        try:
            self._disable_setgroups()
            self._write_uid_mappings()
            self._write_gid_mappings()
        except Exception as e:
            logger.error(f"Failed to configure permissions: {e}")

        logger.info(f"UID/GID mappings applied for process {self._child_pid}")

    def drop_privileges(self) -> None:
        """Drop user and group privileges to the specified IDs.

        This method sets the real and effective user and group IDs of the
        current process to the specified user and group IDs. This is typically
        used after creating a new namespace and forking a child process to
        ensure the process runs with reduced privileges.

        Raises:
            ValueError: If the user or group ID is not set.
        """
        if self._user_id is None or self._group_id is None:
            raise ValueError("User or group ID not set")

        os.setregid(self._group_id, self._group_id)
        os.setreuid(self._user_id, self._user_id)

        logger.info(f"Dropped priviledges to UID {self._user_id}, GID {self._group_id}")

    def _disable_setgroups(self) -> None:
        with open(f"/proc/{self.child_pid}/setgroups", "wb") as _file:
            _file.write(b"deny")

    def _write_uid_mappings(self) -> None:
        with open(f"/proc/{self._child_pid}/uid_map", "wb") as _file:
            for inside_uid, outside_uid, count in self._uid_mappings:
                _file.write(f"{inside_uid} {outside_uid} {count}\n".encode())

    def _write_gid_mappings(self) -> None:
        with open(f"/proc/{self._child_pid}/gid_map", "wb") as _file:
            for inside_gid, outside_gid, count in self._gid_mappings:
                _file.write(f"{inside_gid} {outside_gid} {count}\n".encode())

    @property
    def user_id(self) -> Optional[int]:
        """Get the user ID for the container.

        Returns:
            The user ID or None if not set.
        """
        return self._user_id

    @property
    def group_id(self) -> Optional[int]:
        """Get the group ID for the container.

        Returns:
            The group ID or None if not set.
        """
        return self._group_id
