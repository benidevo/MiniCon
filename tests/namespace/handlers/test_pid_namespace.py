"""Tests for the PidNamespaceHandler class."""

from unittest.mock import patch

import pytest

from src.namespace.handlers.pid_namespace import PidNamespaceHandler


def test_should_fail_when_unshare_fails(mock_libc_unshare):
    handler = PidNamespaceHandler()
    mock_libc_unshare.unshare.return_value = -1
    mock_libc_unshare.unshare.side_effect = lambda x: -1  # Simulate error

    with pytest.raises(OSError, match="unshare failed"):
        handler.setup()


def test_should_create_pid_namespace_when_setup_called(mock_libc_unshare):
    handler = PidNamespaceHandler()
    handler.setup()
    mock_libc_unshare.unshare.assert_called_once_with(0x20000000)  # CLONE_NEWPID


def test_should_fork_child_when_fork_in_new_namespace_called():
    handler = PidNamespaceHandler()

    with patch("os.fork", return_value=1234) as mock_fork:
        child_pid = handler.fork_in_new_namespace(lambda: 0)

    mock_fork.assert_called_once()
    assert child_pid == 1234


def test_should_return_child_pid_when_fork_succeeds():
    handler = PidNamespaceHandler()

    with patch("os.fork", return_value=5678):
        child_pid = handler.fork_in_new_namespace(lambda: 0)

    assert child_pid == 5678
    assert handler.child_pid == 5678


def test_should_run_child_function_when_forked():
    handler = PidNamespaceHandler()

    def mock_child_func():
        with open("/tmp/test_child_process.txt", "w") as f:
            f.write("Child process executed")
        return 0

    with patch("os.fork", return_value=0):
        with patch("os._exit") as mock_exit:
            handler.fork_in_new_namespace(mock_child_func)

    with open("/tmp/test_child_process.txt", "r") as f:
        content = f.read()

    assert content == "Child process executed"
    mock_exit.assert_called_once_with(0)
