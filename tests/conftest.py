"""Test fixtures for MiniCon."""

import json
from unittest.mock import MagicMock, mock_open, patch

import pytest

from src.container.model import Container
from src.container.registry import ContainerRegistry

ONE_HUNDRED_MEGABYTES = 100 * 1024 * 1024


@pytest.fixture
def sample_container():
    return Container(
        name="test-container",
        id="abc123",
        process_id=12345,
        command=["python", "-m", "http.server"],
        root_fs="/var/lib/minicon/rootfs/abc123",
        hostname="test-container",
        memory_limit=ONE_HUNDRED_MEGABYTES,
    )


@pytest.fixture
def registry_file_content(sample_container):
    return {
        "abc123": sample_container.to_dict(),
        "def456": {
            "name": "another-container",
            "id": "def456",
            "process_id": 67890,
            "command": ["nginx"],
            "root_fs": "/var/lib/minicon/rootfs/def456",
            "hostname": "another-container",
            "memory_limit": 1024 * 1024 * 200,
            "state": "running",
            "exit_code": None,
            "created_at": "2023-01-02T12:00:00",
            "started_at": "2023-01-02T12:01:00",
            "exited_at": None,
        },
    }


@pytest.fixture
def mock_registry_file(registry_file_content):
    with (
        patch("os.path.exists", return_value=True),
        patch("builtins.open", mock_open(read_data=json.dumps(registry_file_content))),
    ):
        yield


@pytest.fixture
def registry(mock_registry_file):
    return ContainerRegistry(registry_file="test_containers.json")


@pytest.fixture
def mock_libc_unshare():
    with patch("ctypes.CDLL") as mock_cdll:
        mock_libc = MagicMock()
        mock_libc.unshare.return_value = 0
        mock_cdll.return_value = mock_libc
        yield mock_libc
