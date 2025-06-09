"""Tests for security utilities."""

import subprocess
import tempfile
from unittest.mock import Mock, patch

import pytest

from src.utils.security import (
    SecurityError,
    is_safe_path,
    safe_copy_directory,
    safe_extract_tar,
    safe_make_mount_private,
    safe_mount_proc,
    safe_set_hostname,
    validate_command,
    validate_container_name,
)


def test_should_accept_valid_paths_when_within_base():
    assert is_safe_path("/var/lib/minicon/test", "/var/lib/minicon")
    assert is_safe_path("/var/lib/minicon/containers/abc123", "/var/lib/minicon")


def test_should_reject_paths_when_directory_traversal_attempted():
    assert not is_safe_path("/var/lib/minicon/../etc/passwd", "/var/lib/minicon")
    assert not is_safe_path("../../../etc/passwd", "/var/lib/minicon")
    assert not is_safe_path("/etc/passwd", "/var/lib/minicon")


def test_should_reject_paths_when_outside_base_directory():
    assert not is_safe_path("/nonexistent/../../etc", "/var/lib/minicon")


def test_should_accept_valid_container_names():
    assert validate_container_name("test-container")
    assert validate_container_name("test_container")
    assert validate_container_name("TestContainer123")
    assert validate_container_name("a")


def test_should_reject_empty_container_name():
    assert not validate_container_name("")


def test_should_reject_container_names_with_invalid_characters():
    assert not validate_container_name("test/container")  # Slash
    assert not validate_container_name("test container")  # Space
    assert not validate_container_name("test;container")  # Semicolon
    assert not validate_container_name("test$container")  # Dollar sign


def test_should_reject_container_names_when_too_long():
    assert not validate_container_name("a" * 65)


def test_should_accept_safe_commands():
    assert validate_command(["echo", "hello"])
    assert validate_command(["python3", "-c", "print('hello')"])
    assert validate_command(["ls", "-la"])


def test_should_reject_empty_command():
    assert not validate_command([])


def test_should_reject_dangerous_commands():
    assert not validate_command(["rm", "-rf", "/"])
    assert not validate_command(["sudo", "echo", "hello"])
    assert not validate_command(["mount", "/dev/sda1", "/mnt"])


@patch("src.utils.security.subprocess.run")
@patch("src.utils.security.os.path.exists")
@patch("src.utils.security.os.path.isdir")
@patch("src.utils.security.is_safe_path")
def test_should_copy_directory_when_paths_are_safe(
    mock_is_safe_path, mock_isdir, mock_exists, mock_subprocess
):
    mock_is_safe_path.return_value = True
    mock_exists.return_value = True
    mock_isdir.return_value = True
    mock_subprocess.return_value = Mock(returncode=0)

    safe_copy_directory("/source", "/dest")

    mock_subprocess.assert_called_once_with(
        ["cp", "-a", "/source/.", "/dest"],
        check=True,
        capture_output=True,
        text=True,
    )


@patch("src.utils.security.os.path.exists")
@patch("src.utils.security.os.path.isdir")
@patch("src.utils.security.is_safe_path")
def test_should_fail_copy_when_source_path_unsafe(
    mock_is_safe_path, mock_isdir, mock_exists
):
    mock_exists.return_value = True
    mock_isdir.return_value = True
    mock_is_safe_path.side_effect = [True, False]  # dest safe, source unsafe

    with pytest.raises(SecurityError, match="Unsafe source path"):
        safe_copy_directory("/unsafe/../source", "/dest")


@patch("src.utils.security.os.path.exists")
@patch("src.utils.security.os.path.isdir")
@patch("src.utils.security.is_safe_path")
def test_should_fail_copy_when_destination_path_unsafe(
    mock_is_safe_path, mock_isdir, mock_exists
):
    mock_exists.return_value = True
    mock_isdir.return_value = True
    mock_is_safe_path.side_effect = [False]  # dest unsafe (first call)

    with pytest.raises(SecurityError, match="Unsafe destination path"):
        safe_copy_directory("/source", "/unsafe/../dest")


@patch("src.utils.security.os.path.exists")
def test_should_fail_copy_when_source_not_exists(mock_exists):
    mock_exists.return_value = False

    with pytest.raises(SecurityError, match="Invalid source directory"):
        safe_copy_directory("/nonexistent", "/dest")


@patch("src.utils.security.subprocess.run")
@patch("src.utils.security.os.path.exists")
@patch("src.utils.security.is_safe_path")
def test_should_extract_tar_when_file_valid(
    mock_is_safe_path, mock_exists, mock_subprocess
):
    mock_is_safe_path.return_value = True
    mock_exists.return_value = True
    mock_subprocess.return_value = Mock(returncode=0)

    safe_extract_tar("/path/to/file.tar", "/dest")

    mock_subprocess.assert_called_once_with(
        ["tar", "-xf", "/path/to/file.tar", "-C", "/dest"],
        check=True,
        capture_output=True,
        text=True,
    )


@patch("src.utils.security.os.path.exists")
def test_should_fail_extract_when_tar_file_not_exists(mock_exists):
    mock_exists.return_value = False

    with pytest.raises(SecurityError, match="Invalid tar file"):
        safe_extract_tar("/nonexistent.tar", "/dest")


@patch("src.utils.security.os.path.exists")
def test_should_fail_extract_when_file_not_tar(mock_exists):
    mock_exists.return_value = True

    with pytest.raises(SecurityError, match="Invalid tar file"):
        safe_extract_tar("/file.txt", "/dest")


@patch("src.utils.security.subprocess.run")
@patch("src.utils.security.is_safe_path")
def test_should_mount_proc_when_path_safe(mock_is_safe_path, mock_subprocess):
    mock_is_safe_path.return_value = True
    mock_subprocess.return_value = Mock(returncode=0)

    safe_mount_proc("/proc")

    mock_subprocess.assert_called_once_with(
        ["mount", "-t", "proc", "proc", "/proc"],
        check=True,
        capture_output=True,
        text=True,
    )


@patch("src.utils.security.is_safe_path")
def test_should_fail_mount_proc_when_path_unsafe(mock_is_safe_path):
    mock_is_safe_path.return_value = False

    with pytest.raises(SecurityError, match="Unsafe proc path"):
        safe_mount_proc("/unsafe/../proc")


@patch("src.utils.security.subprocess.run")
def test_should_set_hostname_when_valid(mock_subprocess):
    mock_subprocess.return_value = Mock(returncode=0)

    safe_set_hostname("test-hostname")

    mock_subprocess.assert_called_once_with(
        ["hostname", "test-hostname"], check=True, capture_output=True, text=True
    )


def test_should_fail_set_hostname_when_empty():
    with pytest.raises(SecurityError, match="Invalid hostname length"):
        safe_set_hostname("")


def test_should_fail_set_hostname_when_too_long():
    with pytest.raises(SecurityError, match="Invalid hostname length"):
        safe_set_hostname("a" * 254)


def test_should_fail_set_hostname_when_invalid_characters():
    with pytest.raises(SecurityError, match="Invalid hostname characters"):
        safe_set_hostname("test$hostname")

    with pytest.raises(SecurityError, match="Invalid hostname characters"):
        safe_set_hostname("test hostname")


@patch("src.utils.security.subprocess.run")
def test_should_make_mount_private_when_called(mock_subprocess):
    mock_subprocess.return_value = Mock(returncode=0)

    safe_make_mount_private()

    mock_subprocess.assert_called_once_with(
        ["mount", "--make-private", "/"], check=True, capture_output=True, text=True
    )


@patch("src.utils.security.subprocess.run")
def test_should_propagate_subprocess_error(mock_subprocess):
    mock_subprocess.side_effect = subprocess.CalledProcessError(
        1, ["command"], stderr="Command failed"
    )

    with pytest.raises(subprocess.CalledProcessError):
        safe_make_mount_private()


def test_should_validate_paths_in_real_directories():
    with tempfile.TemporaryDirectory() as temp_dir:
        assert is_safe_path(f"{temp_dir}/subdir", temp_dir)
        assert not is_safe_path("/etc/passwd", temp_dir)


def test_should_validate_all_safe_commands():
    safe_commands = [
        ["echo", "hello", "world"],
        ["python3", "-c", "print('test')"],
        ["cat", "/tmp/test.txt"],
        ["grep", "pattern", "file.txt"],
    ]

    for cmd in safe_commands:
        assert validate_command(cmd), f"Command should be safe: {cmd}"


def test_should_reject_all_dangerous_commands():
    dangerous_commands = [
        ["rm", "-rf", "/"],
        ["sudo", "anything"],
        ["mount", "/dev/sda1", "/mnt"],
        ["chmod", "777", "/etc/passwd"],
    ]

    for cmd in dangerous_commands:
        assert not validate_command(cmd), f"Command should be dangerous: {cmd}"
