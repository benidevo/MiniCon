"""Tests for the ContainerManager class."""

from unittest.mock import patch

import pytest

from src.container.manager import ContainerManager
from src.container.model import State


def test_should_create_container_with_unique_id(manager):
    with patch("uuid.uuid4", return_value="abcdef1234567890"):
        container_id = manager.create("test-container", ["python", "-m", "http.server"])

        assert container_id == "abcdef12"
        container = manager.registry.get_container(container_id)
        assert container is not None
        assert container.name == "test-container"
        assert container.command == ["python", "-m", "http.server"]
        assert container.state == State.CREATED


def test_should_prepare_rootfs_during_container_creation(manager):
    with (
        patch("uuid.uuid4", return_value="abcdef1234567890"),
        patch("os.makedirs") as mock_makedirs,
        patch("os.system") as mock_system,
    ):
        container_id = manager.create("test-container", ["python", "-m", "http.server"])

        mock_makedirs.assert_called()

        mock_system.assert_called_with(
            f"cp -a /var/lib/minicon/base/* /var/lib/minicon/rootfs/{container_id}/"
        )

        container = manager.registry.get_container(container_id)
        assert container.root_fs == f"/var/lib/minicon/rootfs/{container_id}"


def test_should_start_container_when_in_created_state(manager, mock_orchestrator):
    with (
        patch("threading.Thread"),
        patch.object(manager, "_orchestrator_class", return_value=mock_orchestrator),
    ):
        container_id = "abc123"
        container = manager.registry.get_container(container_id)
        container.state = State.CREATED

        manager.start(container_id)

        container = manager.registry.get_container(container_id)
        assert container.state == State.RUNNING
        assert container.process_id == 12345  # PID from mock_orchestrator

        mock_orchestrator.configure.assert_called_once()
        mock_orchestrator.create_container_process.assert_called_once()

        assert container_id in manager._orchestrators


def test_should_fail_to_start_nonexistent_container(manager):
    with pytest.raises(ValueError, match="Container nonexistent not found"):
        manager.start("nonexistent")


def test_should_fail_to_start_non_created_container(manager):
    container_id = "def456"

    with pytest.raises(
        ValueError, match=f"Container {container_id} is not in the created state"
    ):
        manager.start(container_id)


def test_should_stop_running_container(manager, mock_orchestrator):
    container_id = "def456"
    container = manager.registry.get_container(container_id)
    if container.state != State.RUNNING:
        container.state = State.RUNNING

    manager._orchestrators[container_id] = mock_orchestrator

    result = manager.stop(container_id)

    assert result is True
    mock_orchestrator.terminate.assert_called_once()

    container = manager.registry.get_container(container_id)
    assert container.state == State.EXITED


def test_should_fail_to_stop_nonexistent_container(manager):
    with pytest.raises(ValueError, match="Container nonexistent not found"):
        manager.stop("nonexistent")


def test_should_fail_to_stop_non_running_container(manager):
    container_id = "abc123"

    with pytest.raises(
        ValueError, match=f"Container {container_id} is not in the running state"
    ):
        manager.stop(container_id)


def test_should_remove_exited_container(manager):
    container_id = "abc123"

    manager.registry.update_container_state(container_id, State.EXITED)

    manager.remove(container_id)

    assert manager.registry.get_container(container_id) is None


def test_should_fail_to_remove_running_container(manager):
    container_id = "def456"
    container = manager.registry.get_container(container_id)
    container.state = State.RUNNING

    with pytest.raises(
        ValueError, match=f"Cannot remove running container {container_id}"
    ):
        manager.remove(container_id)


def test_should_list_all_containers(manager):
    containers = manager.list()

    assert len(containers) == 2
    assert any(c.id == "abc123" for c in containers)
    assert any(c.id == "def456" for c in containers)


def test_should_list_containers_filtered_by_state(manager):
    manager.registry.update_container_state("abc123", State.EXITED)
    manager.registry.update_container_state("def456", State.RUNNING)

    running_containers = manager.list(State.RUNNING)
    exited_containers = manager.list(State.EXITED)

    assert len(running_containers) == 1
    assert running_containers[0].id == "def456"

    assert len(exited_containers) == 1
    assert exited_containers[0].id == "abc123"


def test_should_monitor_container_and_update_state_on_exit(manager, mock_orchestrator):
    container_id = "def456"
    manager._orchestrators[container_id] = mock_orchestrator
    mock_orchestrator.wait_for_exit.return_value = 0

    manager._monitor_container(container_id)

    container = manager.registry.get_container(container_id)
    assert container.state == State.EXITED
    assert container.exit_code == 0

    assert container_id not in manager._orchestrators


def test_should_recover_running_containers_on_init(mock_registry_file):
    with (
        patch("os.kill", side_effect=lambda pid, sig: True),
        patch("src.container.manager.ContainerManager.start") as mock_start,
        patch("os.makedirs"),
        patch("os.path.exists", return_value=True),
        patch("src.container.registry.ContainerRegistry._save_to_file"),
    ):

        ContainerManager()

        mock_start.assert_called_once_with("def456")


def test_should_not_recover_container_when_process_not_running(mock_registry_file):
    with (
        patch("os.kill", side_effect=OSError()),
        patch("src.container.manager.ContainerManager.start") as mock_start,
        patch("os.makedirs"),
        patch("os.path.exists", return_value=True),
        patch("src.container.registry.ContainerRegistry._save_to_file"),
    ):

        manager = ContainerManager()
        mock_start.assert_not_called()

        running_containers = manager.registry.get_all_containers(State.RUNNING)
        assert len(running_containers) == 0
