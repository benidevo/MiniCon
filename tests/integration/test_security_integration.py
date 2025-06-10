"""Integration tests for security implementations."""

import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.container.manager import ContainerManager
from src.container.model import State
from src.utils.security import SecurityError


def test_should_create_container_when_security_validation_passes():
    with tempfile.TemporaryDirectory() as temp_dir:
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
            manager = ContainerManager()
            manager.registry._registry_file = f"{temp_dir}/containers.json"

            container_id = manager.create("valid-name", ["echo", "hello"])
            assert len(container_id) == 8

            container = manager.registry.get_container(container_id)
            assert container is not None
            assert container.name == "valid-name"
            assert container.command == ["echo", "hello"]


def test_should_reject_invalid_container_names():
    with tempfile.TemporaryDirectory() as temp_dir:
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
            manager = ContainerManager()
            manager.registry._registry_file = f"{temp_dir}/containers.json"

            valid_names = ["test", "test-container", "test_container", "Test123"]
            for name in valid_names:
                container_id = manager.create(name, ["echo", "hello"])
                assert len(container_id) == 8

            invalid_names = [
                "",
                "test container",
                "test/container",
                "test;container",
                "test$container",
                "a" * 65,
            ]
            for name in invalid_names:
                with pytest.raises(ValueError, match="Invalid container name"):
                    manager.create(name, ["echo", "hello"])


def test_should_reject_dangerous_commands():
    with tempfile.TemporaryDirectory() as temp_dir:
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
            manager = ContainerManager()
            manager.registry._registry_file = f"{temp_dir}/containers.json"

            valid_commands = [
                ["echo", "hello"],
                ["python3", "-c", "print('test')"],
                ["cat", "/tmp/file.txt"],
                ["ls", "-la"],
            ]
            for cmd in valid_commands:
                container_id = manager.create(f"test-{len(cmd)}", cmd)
                assert len(container_id) == 8

            invalid_commands = [
                [],
                ["rm", "-rf", "/"],
                ["sudo", "echo", "hello"],
                ["mount", "/dev/sda1"],
            ]
            for cmd in invalid_commands:
                with pytest.raises(ValueError, match="Invalid or dangerous command"):
                    manager.create("test", cmd)


@patch("src.container.manager.safe_copy_directory")
def test_should_use_secure_copy_when_base_image_is_directory(mock_safe_copy):
    with tempfile.TemporaryDirectory() as temp_dir:
        import os

        base_dir = f"{temp_dir}/base"
        os.makedirs(base_dir)

        with (
            patch("src.container.manager.MINICON_BASE_DIR", temp_dir),
            patch("src.container.manager.MINICON_ROOTFS_DIR", f"{temp_dir}/rootfs"),
            patch("src.container.manager.MINICON_BASE_IMAGE", base_dir),
            patch("src.constants.DEFAULT_SAFE_PATH_BASE", temp_dir),
            patch("src.container.manager.os.makedirs"),
            patch("src.container.manager.os.path.exists") as mock_exists,
            patch("src.container.manager.os.path.isdir") as mock_isdir,
            patch("builtins.open", new_callable=MagicMock),
            patch("src.container.registry.os.makedirs"),
            patch("src.container.registry.os.replace"),
        ):
            # Mock exists/isdir to return True for base_dir check
            def exists_side_effect(path):
                return path == base_dir

            def isdir_side_effect(path):
                return path == base_dir

            mock_exists.side_effect = exists_side_effect
            mock_isdir.side_effect = isdir_side_effect

            manager = ContainerManager()
            manager.registry._registry_file = f"{temp_dir}/containers.json"

            container_id = manager.create("test", ["echo", "hello"])

            mock_safe_copy.assert_called_once()

            args = mock_safe_copy.call_args[0]
            source_path, dest_path = args
            assert source_path == base_dir
            assert dest_path == f"{temp_dir}/rootfs/{container_id}"


@patch("src.container.manager.safe_extract_tar")
def test_should_use_secure_extraction_when_base_image_is_tar(mock_extract_tar):
    with tempfile.TemporaryDirectory() as temp_dir:
        base_tar = f"{temp_dir}/base.tar"
        with open(base_tar, "w") as f:
            f.write("dummy tar content")

        with (
            patch("src.container.manager.MINICON_BASE_DIR", temp_dir),
            patch("src.container.manager.MINICON_ROOTFS_DIR", f"{temp_dir}/rootfs"),
            patch("src.container.manager.MINICON_BASE_IMAGE", base_tar),
            patch("src.constants.DEFAULT_SAFE_PATH_BASE", temp_dir),
            patch("src.container.manager.os.makedirs"),
            patch("src.container.manager.os.path.exists") as mock_exists,
            patch("src.container.manager.os.path.isfile") as mock_isfile,
            patch("builtins.open", new_callable=MagicMock),
            patch("src.container.registry.os.makedirs"),
            patch("src.container.registry.os.replace"),
        ):
            # Mock exists/isfile to return True for base_tar check
            def exists_side_effect(path):
                return path == base_tar

            def isfile_side_effect(path):
                return path == base_tar and path.endswith(".tar")

            mock_exists.side_effect = exists_side_effect
            mock_isfile.side_effect = isfile_side_effect

            manager = ContainerManager()
            manager.registry._registry_file = f"{temp_dir}/containers.json"

            container_id = manager.create("test", ["echo", "hello"])

            mock_extract_tar.assert_called_once()

            args = mock_extract_tar.call_args[0]
            tar_path, dest_path = args
            assert tar_path == base_tar
            assert dest_path == f"{temp_dir}/rootfs/{container_id}"


@patch("src.container.manager.threading.Thread")
@patch("src.namespace.orchestrator.NamespaceOrchestrator")
def test_should_complete_lifecycle_when_security_validated(
    mock_orchestrator_class, mock_thread_class
):
    mock_orchestrator = Mock()
    mock_orchestrator.create_container_process.return_value = 12345
    mock_orchestrator_class.return_value = mock_orchestrator

    # Mock thread to prevent actual thread creation
    mock_thread = MagicMock()
    mock_thread_class.return_value = mock_thread

    with tempfile.TemporaryDirectory() as temp_dir:
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
            manager = ContainerManager()
            manager.registry._registry_file = f"{temp_dir}/containers.json"

            container_id = manager.create("secure-test", ["echo", "secure"])

            container = manager.registry.get_container(container_id)
            assert container.state == State.CREATED
            assert container.name == "secure-test"
            assert container.command == ["echo", "secure"]

            manager._orchestrator_class = mock_orchestrator_class
            manager.start(container_id)

            mock_orchestrator.configure.assert_called_once()
            configure_args = mock_orchestrator.configure.call_args[1]
            assert configure_args["hostname"] == "secure-test"
            assert configure_args["command"] == ["echo", "secure"]

            container = manager.registry.get_container(container_id)
            assert container.state == State.RUNNING
            assert container.process_id == 12345


@patch("src.container.manager.safe_copy_directory")
def test_should_propagate_security_errors_during_creation(mock_safe_copy):
    mock_safe_copy.side_effect = SecurityError("Unsafe path detected")

    with tempfile.TemporaryDirectory() as temp_dir:
        import os

        base_dir = f"{temp_dir}/base"
        os.makedirs(base_dir)

        with (
            patch("src.container.manager.MINICON_BASE_DIR", temp_dir),
            patch("src.container.manager.MINICON_ROOTFS_DIR", f"{temp_dir}/rootfs"),
            patch("src.container.manager.MINICON_BASE_IMAGE", base_dir),
            patch("src.constants.DEFAULT_SAFE_PATH_BASE", temp_dir),
            patch("src.container.manager.os.makedirs"),
            patch("src.container.manager.os.path.exists") as mock_exists,
            patch("src.container.manager.os.path.isdir") as mock_isdir,
            patch("builtins.open", new_callable=MagicMock),
            patch("src.container.registry.os.makedirs"),
            patch("src.container.registry.os.replace"),
        ):
            # Mock exists/isdir to return True for base_dir check
            def exists_side_effect(path):
                return path == base_dir

            def isdir_side_effect(path):
                return path == base_dir

            mock_exists.side_effect = exists_side_effect
            mock_isdir.side_effect = isdir_side_effect

            manager = ContainerManager()
            manager.registry._registry_file = f"{temp_dir}/containers.json"

            with pytest.raises(SecurityError, match="Unsafe path detected"):
                manager.create("test", ["echo", "hello"])


@patch("src.namespace.handlers.mount_namespace.safe_make_mount_private")
@patch("src.namespace.handlers.mount_namespace.safe_mount_proc")
@patch("src.namespace.handlers.mount_namespace.os.chroot")
@patch("src.namespace.handlers.mount_namespace.os.chdir")
@patch("src.namespace.handlers.mount_namespace.os.path.exists")
@patch("src.namespace.handlers.mount_namespace.os.mkdir")
def test_should_use_secure_functions_for_mount_namespace(
    mock_mkdir,
    mock_exists,
    mock_chdir,
    mock_chroot,
    mock_safe_mount,
    mock_safe_private,
):
    from src.namespace.handlers.mount_namespace import MountNamespaceHandler

    handler = MountNamespaceHandler()
    handler.set_root_fs("/test/rootfs")
    mock_exists.return_value = False

    handler.apply_mount_isolation()

    mock_safe_private.assert_called_once()
    mock_safe_mount.assert_called_once_with("/proc")
    mock_chroot.assert_called_once_with("/test/rootfs")
    mock_chdir.assert_called_once_with("/")
    mock_mkdir.assert_called_once_with("/proc")


@patch("src.namespace.handlers.uts_namespace.safe_set_hostname")
def test_should_use_secure_functions_for_uts_namespace(mock_safe_hostname):
    from src.namespace.handlers.uts_namespace import UtsNamespaceHandler

    handler = UtsNamespaceHandler()
    handler.set_hostname("test-hostname")

    handler.apply_uts_isolation()

    mock_safe_hostname.assert_called_once_with("test-hostname")


@patch("src.namespace.handlers.uts_namespace.safe_set_hostname")
def test_should_propagate_security_errors_from_namespace_handlers(mock_safe_hostname):
    from src.namespace.handlers.uts_namespace import UtsNamespaceHandler

    mock_safe_hostname.side_effect = SecurityError("Invalid hostname")

    handler = UtsNamespaceHandler()
    handler.set_hostname("invalid-hostname")

    with pytest.raises(SecurityError, match="Invalid hostname"):
        handler.apply_uts_isolation()
