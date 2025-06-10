"""Tests for the UtsNamespaceHandler class."""

from unittest.mock import patch

import pytest

from src.namespace.handlers.uts_namespace import UtsNamespaceHandler


def test_should_fail_when_unshare_fails(mock_libc_unshare):
    handler = UtsNamespaceHandler()
    mock_libc_unshare.unshare.return_value = -1
    mock_libc_unshare.unshare.side_effect = lambda x: -1  # Simulate error

    with pytest.raises(OSError, match="unshare failed"):
        handler.setup()


def test_should_create_uts_namespace_when_setup_called(mock_libc_unshare):
    handler = UtsNamespaceHandler()
    handler.setup()
    mock_libc_unshare.unshare.assert_called_once_with(0x04000000)  # CLONE_NEWUTS


def test_should_set_hostname():
    handler = UtsNamespaceHandler()
    test_hostname = "container1"

    handler.set_hostname(test_hostname)

    assert handler._hostname == test_hostname


def test_should_fork_child_when_fork_in_new_namespace_called():
    handler = UtsNamespaceHandler()

    with patch("os.fork", return_value=1234) as mock_fork:
        child_pid = handler.fork_in_new_namespace(lambda: 0)

    mock_fork.assert_called_once()
    assert child_pid == 1234


def test_should_return_child_pid_when_fork_succeeds():
    handler = UtsNamespaceHandler()

    with patch("os.fork", return_value=5678):
        child_pid = handler.fork_in_new_namespace(lambda: 0)

    assert child_pid == 5678
    assert handler.child_pid == 5678


def test_should_run_child_function_when_forked():
    handler = UtsNamespaceHandler()
    test_file = "/tmp/test_uts_child_process.txt"

    def mock_child_func():
        with open(test_file, "w") as f:
            f.write("UTS child process executed")
        return 0

    with patch("os.fork", return_value=0), patch("os._exit") as mock_exit:
        handler.fork_in_new_namespace(mock_child_func)

    with open(test_file, "r") as f:
        content = f.read()

    assert content == "UTS child process executed"
    mock_exit.assert_called_once_with(0)


def test_should_raise_error_when_applying_uts_isolation_without_hostname():
    handler = UtsNamespaceHandler()

    with pytest.raises(ValueError, match="Hostname not set"):
        handler.apply_uts_isolation()


def test_should_apply_uts_isolation_correctly():
    handler = UtsNamespaceHandler()
    test_hostname = "container-test"
    handler.set_hostname(test_hostname)

    with patch(
        "src.namespace.handlers.uts_namespace.safe_set_hostname"
    ) as mock_safe_hostname:
        handler.apply_uts_isolation()

        mock_safe_hostname.assert_called_once_with(test_hostname)


def test_should_use_safe_set_hostname_when_applying_uts_isolation():
    handler = UtsNamespaceHandler()
    test_hostname = "container-test"
    handler.set_hostname(test_hostname)

    with patch(
        "src.namespace.handlers.uts_namespace.safe_set_hostname"
    ) as mock_safe_hostname:
        handler.apply_uts_isolation()
        mock_safe_hostname.assert_called_once_with(test_hostname)
