"""Integration tests for security validation functionality."""

import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from src.container.manager import ContainerManager
from src.utils.security import (
    SecurityError,
    validate_command,
    validate_container_name,
)


def test_should_validate_container_names_when_using_manager():
    temp_dir = tempfile.mkdtemp()

    try:
        manager = ContainerManager()

        valid_names = [
            "test",
            "test-container",
            "test_container",
            "Test123",
            "a",
            "web-server-1",
        ]

        for name in valid_names:
            with (
                patch("src.container.manager.MINICON_BASE_DIR", temp_dir),
                patch("src.container.manager.MINICON_ROOTFS_DIR", f"{temp_dir}/rootfs"),
                patch("src.container.manager.MINICON_BASE_IMAGE", f"{temp_dir}/base"),
                patch("src.constants.DEFAULT_SAFE_PATH_BASE", temp_dir),
                patch("src.container.manager.os.makedirs"),
                patch("src.container.manager.os.path.exists", return_value=False),
                patch("builtins.open", new_callable=MagicMock),
                patch("src.container.registry.os.makedirs"),
                patch("src.container.registry.os.replace"),
            ):

                try:
                    container_id = manager.create(name, ["echo", "hello"])
                    msg = f"Failed to create container with valid name: {name}"
                    assert len(container_id) == 8, msg
                except ValueError as e:
                    if "Invalid container name" in str(e):
                        pytest.fail(
                            f"Valid container name '{name}' was incorrectly rejected"
                        )

        invalid_names = [
            "",
            "test container",
            "test/container",
            "test;container",
            "test$container",
            "test|container",
            "test&container",
            "a" * 65,
        ]

        for name in invalid_names:
            with (
                patch("src.container.manager.MINICON_BASE_DIR", temp_dir),
                patch("src.container.manager.MINICON_ROOTFS_DIR", f"{temp_dir}/rootfs"),
                patch("src.container.manager.MINICON_BASE_IMAGE", f"{temp_dir}/base"),
                patch("src.constants.DEFAULT_SAFE_PATH_BASE", temp_dir),
                patch("src.container.manager.os.makedirs"),
                patch("src.container.manager.os.path.exists", return_value=False),
                patch("builtins.open", new_callable=MagicMock),
                patch("src.container.registry.os.makedirs"),
                patch("src.container.registry.os.replace"),
            ):
                with pytest.raises(ValueError, match="Invalid container name"):
                    manager.create(name, ["echo", "hello"])
    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


def test_should_validate_commands_when_using_manager():
    temp_dir = tempfile.mkdtemp()

    try:
        manager = ContainerManager()

        valid_commands = [
            ["echo", "hello", "world"],
            ["python3", "-c", "print('Hello')"],
            ["cat", "/tmp/test.txt"],
            ["ls", "-la", "/home"],
            ["grep", "pattern", "file.txt"],
            ["awk", "{print $1}", "file.txt"],
            ["sed", "s/old/new/g", "file.txt"],
            ["sort", "-n", "numbers.txt"],
            ["head", "-10", "file.txt"],
            ["tail", "-f", "log.txt"],
        ]

        for cmd in valid_commands:
            with (
                patch("src.container.manager.MINICON_BASE_DIR", temp_dir),
                patch("src.container.manager.MINICON_ROOTFS_DIR", f"{temp_dir}/rootfs"),
                patch("src.container.manager.MINICON_BASE_IMAGE", f"{temp_dir}/base"),
                patch("src.constants.DEFAULT_SAFE_PATH_BASE", temp_dir),
                patch("src.container.manager.os.makedirs"),
                patch("src.container.manager.os.path.exists", return_value=False),
                patch("builtins.open", new_callable=MagicMock),
                patch("src.container.registry.os.makedirs"),
                patch("src.container.registry.os.replace"),
            ):

                try:
                    container_id = manager.create("test", cmd)
                    assert (
                        len(container_id) == 8
                    ), f"Failed to create container with valid command: {cmd}"
                except ValueError as e:
                    if "Invalid or dangerous command" in str(e):
                        pytest.fail(f"Valid command '{cmd}' was incorrectly rejected")

        dangerous_commands = [
            [],
            ["rm", "-rf", "/"],
            ["sudo", "anything"],
            ["su", "root"],
            ["mount", "/dev/sda1", "/mnt"],
            ["umount", "/mnt"],
            ["chmod", "777", "/etc/passwd"],
            ["chown", "root:root", "/etc"],
            ["dd", "if=/dev/zero", "of=/dev/sda"],
            ["mkfs", "/dev/sda1"],
            ["fdisk", "/dev/sda"],
            ["parted", "/dev/sda"],
        ]

        for cmd in dangerous_commands:
            with (
                patch("src.container.manager.MINICON_BASE_DIR", temp_dir),
                patch("src.container.manager.MINICON_ROOTFS_DIR", f"{temp_dir}/rootfs"),
                patch("src.container.manager.MINICON_BASE_IMAGE", f"{temp_dir}/base"),
                patch("src.constants.DEFAULT_SAFE_PATH_BASE", temp_dir),
                patch("src.container.manager.os.makedirs"),
                patch("src.container.manager.os.path.exists", return_value=False),
                patch("builtins.open", new_callable=MagicMock),
                patch("src.container.registry.os.makedirs"),
                patch("src.container.registry.os.replace"),
            ):
                manager.registry._registry_file = f"{temp_dir}/containers.json"
                with pytest.raises(ValueError, match="Invalid or dangerous command"):
                    manager.create("test", cmd)
    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


def test_should_prevent_path_traversal_when_using_filesystem():
    temp_dir = tempfile.mkdtemp()

    try:
        manager = ContainerManager()

        with (
            patch("src.container.manager.MINICON_BASE_DIR", temp_dir),
            patch("src.container.manager.MINICON_ROOTFS_DIR", f"{temp_dir}/rootfs"),
            patch("src.container.manager.MINICON_BASE_IMAGE", f"{temp_dir}/base"),
            patch("src.constants.DEFAULT_SAFE_PATH_BASE", temp_dir),
            patch("src.container.manager.os.makedirs"),
            patch("src.container.manager.os.path.exists", return_value=True),
            patch("src.container.manager.os.path.isdir", return_value=True),
            patch("src.container.manager.safe_copy_directory") as mock_copy,
            patch("builtins.open", new_callable=MagicMock),
            patch("src.container.registry.os.makedirs"),
            patch("src.container.registry.os.replace"),
        ):
            manager.registry._registry_file = f"{temp_dir}/containers.json"

            container_id = manager.create("test", ["echo", "hello"])

            mock_copy.assert_called_once()

            args = mock_copy.call_args[0]
            source_path, dest_path = args
            assert source_path == f"{temp_dir}/base"
            assert dest_path == f"{temp_dir}/rootfs/{container_id}"
    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


def test_should_validate_names_and_commands_properly():
    assert validate_container_name("valid-name")
    assert validate_container_name("valid_name")
    assert validate_container_name("ValidName123")

    assert not validate_container_name("")
    assert not validate_container_name("invalid name")
    assert not validate_container_name("invalid/name")
    assert not validate_container_name("a" * 65)

    assert validate_command(["echo", "hello"])
    assert validate_command(["python3", "-c", "print('test')"])
    assert validate_command(["ls", "-la"])

    assert not validate_command([])
    assert not validate_command(["rm", "-rf", "/"])
    assert not validate_command(["sudo", "anything"])
    assert not validate_command(["mount", "/dev/sda1"])


@pytest.mark.skipif(sys.platform != "linux", reason="Requires Linux")
def test_should_complete_workflow_when_dependencies_mocked():
    temp_dir = tempfile.mkdtemp()

    try:
        with (
            patch("src.container.manager.MINICON_BASE_DIR", temp_dir),
            patch("src.container.manager.MINICON_ROOTFS_DIR", f"{temp_dir}/rootfs"),
            patch("src.container.manager.MINICON_BASE_IMAGE", f"{temp_dir}/base"),
            patch("src.constants.DEFAULT_SAFE_PATH_BASE", temp_dir),
            patch("src.container.manager.os.makedirs") as mock_makedirs,
            patch("src.container.manager.os.path.exists", return_value=False),
            patch("builtins.open", new_callable=MagicMock),
            patch("src.container.registry.os.makedirs"),
            patch("src.container.registry.os.replace"),
            patch(
                "src.namespace.orchestrator.NamespaceOrchestrator"
            ) as mock_orch_class,
        ):

            mock_orch = MagicMock()
            mock_orch.create_container_process.return_value = 12345
            mock_orch_class.return_value = mock_orch

            manager = ContainerManager()
            manager.registry._registry_file = f"{temp_dir}/containers.json"

            container_id = manager.create("integration-test", ["echo", "hello"])

            assert len(container_id) == 8
            container = manager.registry.get_container(container_id)
            assert container is not None
            assert container.name == "integration-test"
            assert container.command == ["echo", "hello"]

            assert mock_makedirs.call_count >= 2

            manager.start(container_id)

            mock_orch.configure.assert_called_once()
            config_kwargs = mock_orch.configure.call_args[1]
            assert config_kwargs["hostname"] == "integration-test"
            assert config_kwargs["command"] == ["echo", "hello"]

            manager.stop(container_id)
            mock_orch.terminate.assert_called_once()

            manager.remove(container_id)

            container = manager.registry.get_container(container_id)
            assert container is None
    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


def test_should_handle_security_errors_properly():
    temp_dir = tempfile.mkdtemp()

    try:
        manager = ContainerManager()

        with (
            patch("src.container.manager.MINICON_BASE_DIR", temp_dir),
            patch("src.container.manager.MINICON_ROOTFS_DIR", f"{temp_dir}/rootfs"),
            patch("src.container.manager.MINICON_BASE_IMAGE", f"{temp_dir}/base"),
            patch("src.constants.DEFAULT_SAFE_PATH_BASE", temp_dir),
            patch("src.container.manager.os.makedirs"),
            patch("src.container.manager.os.path.exists", return_value=True),
            patch("src.container.manager.os.path.isdir", return_value=True),
            patch("src.container.manager.safe_copy_directory") as mock_copy,
        ):
            manager.registry._registry_file = f"{temp_dir}/containers.json"

            mock_copy.side_effect = SecurityError("Path traversal attempt detected")

            with pytest.raises(SecurityError, match="Path traversal attempt detected"):
                manager.create("test", ["echo", "hello"])
    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


def test_should_validate_multiple_layers_together():
    manager = ContainerManager()

    with pytest.raises(ValueError, match="Invalid container name"):
        manager.create("invalid/name", ["rm", "-rf", "/"])

    with pytest.raises(ValueError, match="Invalid container name"):
        manager.create("invalid name", ["echo", "hello"])

    with pytest.raises(ValueError, match="Invalid or dangerous command"):
        manager.create("valid-name", ["rm", "-rf", "/"])
