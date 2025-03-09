"""Tests for the ContainerRegistry."""

from datetime import datetime
from unittest.mock import mock_open, patch

from src.container.model import Container, State
from src.container.registry import ContainerRegistry


def test_should_create_empty_registry_when_no_file_exists():
    with patch("os.path.exists", return_value=False):
        registry = ContainerRegistry(registry_file="nonexistent.json")
        assert registry._containers == {}


def test_should_load_containers_when_registry_file_exists(registry):
    assert len(registry._containers) == 2
    assert "abc123" in registry._containers
    assert "def456" in registry._containers

    container = registry._containers["abc123"]
    assert container.name == "test-container"
    assert container.state == State.CREATED

    container = registry._containers["def456"]
    assert container.name == "another-container"
    assert container.state == State.RUNNING


def test_should_save_container_when_added_to_registry(registry, sample_container):
    new_container = Container(
        name="new-container",
        id="ghi789",
        process_id=54321,
        command=["bash"],
        root_fs="/var/lib/minicon/rootfs/ghi789",
        hostname="new-container",
        memory_limit=1024 * 1024 * 50,
    )

    with patch("os.makedirs"), patch("builtins.open", mock_open()), patch("os.replace"):

        registry.save_container(new_container)

        assert "ghi789" in registry._containers
        assert registry._containers["ghi789"] == new_container


def test_should_return_container_when_getting_by_id(registry):
    container = registry.get_container("abc123")
    assert container is not None
    assert container.id == "abc123"
    assert container.name == "test-container"


def test_should_return_none_when_getting_nonexistent_container(registry):
    container = registry.get_container("nonexistent")
    assert container is None


def test_should_return_all_containers_when_requested(registry):
    containers = registry.get_all_containers()
    assert len(containers) == 2
    container_ids = [c.id for c in containers]
    assert "abc123" in container_ids
    assert "def456" in container_ids


def test_should_update_container_state_when_container_exists(registry):
    with patch("os.makedirs"), patch("builtins.open", mock_open()), patch("os.replace"):

        test_time = datetime.now()
        result = registry.update_container_state(
            "abc123", State.RUNNING, started_at=test_time
        )

        assert result is True
        container = registry._containers["abc123"]
        assert container.state == State.RUNNING
        assert container.started_at == test_time


def test_should_return_false_when_updating_nonexistent_container(registry):
    with patch("os.makedirs"), patch("builtins.open", mock_open()), patch("os.replace"):

        result = registry.update_container_state("nonexistent", State.RUNNING)

        assert result is False


def test_should_remove_container_when_container_exists(registry):
    with patch("os.makedirs"), patch("builtins.open", mock_open()), patch("os.replace"):

        result = registry.remove_container("abc123")

        assert result is True
        assert "abc123" not in registry._containers


def test_should_return_false_when_removing_nonexistent_container(registry):
    with patch("os.makedirs"), patch("builtins.open", mock_open()), patch("os.replace"):

        result = registry.remove_container("nonexistent")

        assert result is False
