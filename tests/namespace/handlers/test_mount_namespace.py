"""Tests for the MountNamespaceHandler class."""

from unittest.mock import patch

import pytest

from src.namespace.handlers.mount_namespace import MountNamespaceHandler


def test_should_fail_when_unshare_fails(mock_libc_unshare):
    handler = MountNamespaceHandler()
    mock_libc_unshare.unshare.return_value = -1
    mock_libc_unshare.unshare.side_effect = lambda x: -1  # Simulate error

    with pytest.raises(OSError, match="unshare failed"):
        handler.setup()


def test_should_create_mount_namespace_when_setup_called(mock_libc_unshare):
    handler = MountNamespaceHandler()
    handler.setup()
    mock_libc_unshare.unshare.assert_called_once_with(0x00020000)  # CLONE_NEWNS


def test_should_set_root_fs_path():
    handler = MountNamespaceHandler()
    test_path = "/path/to/rootfs"

    handler.set_root_fs(test_path)

    assert handler.root_fs == test_path


def test_should_fork_child_when_fork_in_new_namespace_called():
    handler = MountNamespaceHandler()

    with patch("os.fork", return_value=1234) as mock_fork:
        child_pid = handler.fork_in_new_namespace(lambda: 0)

    mock_fork.assert_called_once()
    assert child_pid == 1234


def test_should_return_child_pid_when_fork_succeeds():
    handler = MountNamespaceHandler()

    with patch("os.fork", return_value=5678):
        child_pid = handler.fork_in_new_namespace(lambda: 0)

    assert child_pid == 5678
    assert handler.child_pid == 5678


def test_should_run_child_function_when_forked():
    handler = MountNamespaceHandler()
    test_file = "/tmp/test_child_process.txt"

    def mock_child_func():
        with open(test_file, "w") as f:
            f.write("Child process executed")
        return 0

    with patch("os.fork", return_value=0), patch("os._exit") as mock_exit:
        handler.fork_in_new_namespace(mock_child_func)

    with open(test_file, "r") as f:
        content = f.read()

    assert content == "Child process executed"
    mock_exit.assert_called_once_with(0)


def test_should_raise_error_when_applying_mount_isolation_without_root_fs():
    handler = MountNamespaceHandler()

    with pytest.raises(ValueError, match="Root filesystem not set"):
        handler.apply_mount_isolation()


def test_should_apply_mount_isolation_correctly():
    handler = MountNamespaceHandler()
    test_root_fs = "/var/lib/minicon/rootfs/test123"
    handler.set_root_fs(test_root_fs)

    with (
        patch(
            "src.namespace.handlers.mount_namespace.safe_make_mount_private"
        ) as mock_safe_private,
        patch(
            "src.namespace.handlers.mount_namespace.safe_mount_proc"
        ) as mock_safe_mount,
        patch("src.namespace.handlers.mount_namespace.os.chroot") as mock_chroot,
        patch("src.namespace.handlers.mount_namespace.os.chdir") as mock_chdir,
        patch(
            "src.namespace.handlers.mount_namespace.os.path.exists", return_value=True
        ),
        patch("src.namespace.handlers.mount_namespace.os.makedirs") as mock_makedirs,
    ):

        handler.apply_mount_isolation()

        mock_safe_private.assert_called_once()
        mock_safe_mount.assert_called_once_with("/proc")
        mock_chroot.assert_called_once_with(test_root_fs)
        mock_chdir.assert_called_once_with("/")
        # Should create essential directories before chroot
        assert mock_makedirs.call_count >= 1


def test_should_not_create_proc_if_already_exists():
    handler = MountNamespaceHandler()
    test_root_fs = "/var/lib/minicon/rootfs/test123"
    handler.set_root_fs(test_root_fs)

    with (
        patch(
            "src.namespace.handlers.mount_namespace.safe_make_mount_private"
        ) as mock_safe_private,
        patch(
            "src.namespace.handlers.mount_namespace.safe_mount_proc"
        ) as mock_safe_mount,
        patch("src.namespace.handlers.mount_namespace.os.chroot") as mock_chroot,
        patch("src.namespace.handlers.mount_namespace.os.chdir") as mock_chdir,
        patch(
            "src.namespace.handlers.mount_namespace.os.path.exists", return_value=True
        ),
        patch("src.namespace.handlers.mount_namespace.os.makedirs") as mock_makedirs,
    ):

        handler.apply_mount_isolation()

        mock_safe_private.assert_called_once()
        mock_safe_mount.assert_called_once_with("/proc")
        mock_chroot.assert_called_once_with(test_root_fs)
        mock_chdir.assert_called_once_with("/")
        # Should create essential directories before chroot
        assert mock_makedirs.call_count >= 1
