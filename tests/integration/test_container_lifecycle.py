"""Integration tests for complete container lifecycle."""

import os
import sys
import tempfile
from unittest.mock import Mock, patch

import pytest

from src.container.manager import ContainerManager
from src.container.model import State


@pytest.mark.skipif(sys.platform != "linux", reason="Requires Linux")
@patch("src.container.manager.NamespaceOrchestrator")
def test_should_complete_lifecycle_when_security_valid(mock_orchestrator_class):
    temp_dir = tempfile.mkdtemp()

    try:
        mock_orchestrator = Mock()
        mock_orchestrator.create_container_process.return_value = 12345
        mock_orchestrator.wait_for_exit.return_value = 0
        mock_orchestrator_class.return_value = mock_orchestrator

        registry_path = os.path.join(temp_dir, "containers.json")
        os.makedirs(os.path.join(temp_dir, "rootfs"), exist_ok=True)

        with (
            patch("src.container.manager.MINICON_BASE_DIR", temp_dir),
            patch(
                "src.container.manager.MINICON_ROOTFS_DIR",
                os.path.join(temp_dir, "rootfs"),
            ),
            patch(
                "src.container.manager.MINICON_BASE_IMAGE",
                os.path.join(temp_dir, "base"),
            ),
            patch("src.constants.DEFAULT_SAFE_PATH_BASE", temp_dir),
        ):
            manager = ContainerManager()
            manager.registry._registry_file = registry_path

            container_id = manager.create("test-container", ["echo", "hello"])
            assert len(container_id) == 8

            container = manager.registry.get_container(container_id)
            assert container is not None
            assert container.state == State.CREATED
            assert container.name == "test-container"
            assert container.command == ["echo", "hello"]

            manager.start(container_id)
            mock_orchestrator.create_container_process.assert_called_once()

            container = manager.registry.get_container(container_id)
            assert container.state == State.RUNNING
            assert container.process_id == 12345

            manager.stop(container_id)
            mock_orchestrator.terminate.assert_called_once()

            manager.remove(container_id)
            container = manager.registry.get_container(container_id)
            assert container is None
    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


@patch("src.container.manager.os.makedirs")
def test_should_validate_security_constraints_during_creation(mock_makedirs):
    manager = ContainerManager()

    with pytest.raises(ValueError, match="Invalid container name"):
        manager.create("test/container", ["echo", "test"])

    with pytest.raises(ValueError, match="Invalid or dangerous command"):
        manager.create("test-container", ["rm", "-rf", "/"])

    with pytest.raises(ValueError, match="Invalid or dangerous command"):
        manager.create("test-container", [])


def test_should_validate_security_functions_properly():
    from src.utils.security import validate_command, validate_container_name

    assert validate_container_name("valid-container")
    assert validate_container_name("test_123")
    assert validate_command(["echo", "hello"])
    assert validate_command(["python", "-c", "print('test')"])

    assert not validate_container_name("")
    assert not validate_container_name("test/container")
    assert not validate_container_name("test container")
    assert not validate_command([])
    assert not validate_command(["sudo", "rm", "-rf", "/"])
    assert not validate_command(["mount", "/dev/sda1", "/mnt"])


@patch("src.utils.security.subprocess.run")
def test_should_reject_unsafe_paths_in_operations(mock_subprocess):
    from src.utils.security import (
        SecurityError,
        safe_copy_directory,
        safe_mount_proc,
    )

    with pytest.raises(SecurityError, match="Invalid source directory"):
        safe_copy_directory("../../../etc", "/tmp/safe")

    with pytest.raises(SecurityError, match="Unsafe proc path"):
        safe_mount_proc("../../proc")


@patch("src.utils.security.subprocess.run")
def test_should_handle_subprocess_failures_properly(mock_subprocess):
    from subprocess import CalledProcessError

    from src.utils.security import safe_set_hostname

    mock_subprocess.side_effect = CalledProcessError(1, ["hostname"], "Failed")

    with pytest.raises(CalledProcessError):
        safe_set_hostname("test-host")
