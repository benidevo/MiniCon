"""Tests for the UserNamespaceHandler class."""

from unittest.mock import patch

import pytest

from src.namespace.handlers.user_namespace import UserNamespaceHandler


def test_should_fail_when_unshare_fails(mock_libc_unshare):
    handler = UserNamespaceHandler()
    mock_libc_unshare.unshare.return_value = -1
    mock_libc_unshare.unshare.side_effect = lambda x: -1  # Simulate error

    with pytest.raises(OSError, match="unshare failed"):
        handler.setup()


def test_should_create_user_namespace_when_setup_called(mock_libc_unshare):
    handler = UserNamespaceHandler()
    handler.setup()
    mock_libc_unshare.unshare.assert_called_once_with(0x10000000)  # CLONE_NEWUSER


def test_should_set_user_and_group_ids():
    handler = UserNamespaceHandler()
    test_uid = 1000
    test_gid = 1000

    handler.set_user(test_uid, test_gid)

    assert handler.user_id == test_uid
    assert handler.group_id == test_gid


def test_should_add_uid_mapping():
    handler = UserNamespaceHandler()
    handler.add_uid_mapping(0, 1000, 1)

    assert (0, 1000, 1) in handler._uid_mappings
    assert len(handler._uid_mappings) == 1


def test_should_add_gid_mapping():
    handler = UserNamespaceHandler()
    handler.add_gid_mapping(0, 1000, 1)

    assert (0, 1000, 1) in handler._gid_mappings
    assert len(handler._gid_mappings) == 1


def test_should_raise_error_when_applying_user_isolation_without_mappings():
    handler = UserNamespaceHandler()

    with patch("os.fork", return_value=1234):
        handler.fork_in_new_namespace(lambda: 0)

    with pytest.raises(ValueError, match="UID or GID mappings not set"):
        handler.apply_user_isolation()


def test_should_raise_error_when_applying_user_isolation_without_child_process():
    handler = UserNamespaceHandler()
    handler.add_uid_mapping(0, 1000, 1)
    handler.add_gid_mapping(0, 1000, 1)

    with pytest.raises(ValueError, match="Child process not created yet"):
        handler.apply_user_isolation()


def test_should_raise_error_when_dropping_privileges_without_user_id():
    handler = UserNamespaceHandler()

    with pytest.raises(ValueError, match="User or group ID not set"):
        handler.drop_privileges()


def test_should_drop_privileges_correctly():
    handler = UserNamespaceHandler()
    test_uid = 1000
    test_gid = 1000
    handler.set_user(test_uid, test_gid)

    with patch("os.setregid") as mock_setregid, patch("os.setreuid") as mock_setreuid:
        handler.drop_privileges()

        mock_setregid.assert_called_once_with(test_gid, test_gid)
        mock_setreuid.assert_called_once_with(test_uid, test_uid)


def test_should_run_child_function_with_isolation():
    handler = UserNamespaceHandler()
    handler.set_user(1000, 1000)

    with patch("os.setregid") as mock_setregid, patch("os.setreuid") as mock_setreuid:
        handler.drop_privileges()

        mock_setregid.assert_called_once_with(1000, 1000)
        mock_setreuid.assert_called_once_with(1000, 1000)
