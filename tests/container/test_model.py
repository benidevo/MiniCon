"""Tests for the Container model."""

from datetime import datetime

from src.container.model import Container, State


def test_should_initialize_with_correct_defaults():
    container = Container(
        name="test-container",
        id="abc123",
        process_id=12345,
        command=["python", "-m", "http.server"],
        root_fs="/var/lib/minicon/rootfs/abc123",
        hostname="test-container",
        memory_limit=100 * 1024 * 1024,
    )

    assert container.state == State.CREATED
    assert container.exit_code is None
    assert isinstance(container.created_at, datetime)
    assert container.started_at is None
    assert container.exited_at is None


def test_should_convert_to_dict_when_serializing(sample_container):
    container_dict = sample_container.to_dict()

    assert container_dict["name"] == "test-container"
    assert container_dict["id"] == "abc123"
    assert container_dict["state"] == "created"
    assert isinstance(container_dict["created_at"], str)


def test_should_reconstruct_from_dict_when_deserializing():
    container_dict = {
        "name": "test-container",
        "id": "abc123",
        "process_id": 12345,
        "command": ["python", "-m", "http.server"],
        "root_fs": "/var/lib/minicon/rootfs/abc123",
        "hostname": "test-container",
        "memory_limit": 1024 * 1024 * 100,
        "state": "running",
        "exit_code": None,
        "created_at": "2023-01-01T12:00:00",
        "started_at": "2023-01-01T12:01:00",
        "exited_at": None,
    }

    container = Container.from_dict(container_dict)

    assert container.name == "test-container"
    assert container.id == "abc123"
    assert container.state == State.RUNNING
    assert container.created_at == datetime.fromisoformat("2023-01-01T12:00:00")
    assert container.started_at == datetime.fromisoformat("2023-01-01T12:01:00")


def test_should_preserve_data_when_round_trip_json(sample_container):
    json_str = sample_container.to_json()

    restored_container = Container.from_json(json_str)

    assert restored_container.name == sample_container.name
    assert restored_container.id == sample_container.id
    assert restored_container.process_id == sample_container.process_id
    assert restored_container.command == sample_container.command
    assert restored_container.state == sample_container.state


def test_should_transition_states_when_container_lifecycle_progresses(sample_container):
    assert sample_container.state == State.CREATED

    sample_container.state = State.RUNNING
    sample_container.started_at = datetime.now()
    assert sample_container.state == State.RUNNING

    sample_container.state = State.EXITED
    sample_container.exit_code = 0
    sample_container.exited_at = datetime.now()
    assert sample_container.state == State.EXITED
    assert sample_container.exit_code == 0
