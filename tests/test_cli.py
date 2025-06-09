"""Tests for CLI module."""

from unittest.mock import Mock, patch

import pytest
import typer
from typer.testing import CliRunner

from src.cli import MiniConCLI
from src.container.model import Container, State


@pytest.fixture
def cli():
    return MiniConCLI()


@pytest.fixture
def runner():
    return CliRunner()


@patch("src.cli.os.geteuid")
@patch("src.cli.ContainerManager")
def test_should_create_container_when_run_as_root(
    mock_manager_class, mock_geteuid, cli, runner
):
    mock_geteuid.return_value = 0  # Root user
    mock_manager = Mock()
    mock_manager.create.return_value = "test123"
    mock_manager_class.return_value = mock_manager

    result = runner.invoke(
        cli.app, ["create", "--name", "test-container", "echo", "hello"]
    )

    assert result.exit_code == 0
    assert "test123" in result.output
    mock_manager.create.assert_called_once_with("test-container", ["echo", "hello"])


@patch("src.cli.os.geteuid")
def test_should_fail_when_create_run_without_root(mock_geteuid, cli, runner):
    mock_geteuid.return_value = 1000  # Non-root user

    result = runner.invoke(cli.app, ["create", "--name", "test", "echo", "hello"])

    assert result.exit_code == 1
    assert "requires root privileges" in result.output


@patch("src.cli.ContainerManager")
def test_should_show_no_containers_when_list_is_empty(mock_manager_class, cli, runner):
    mock_manager = Mock()
    mock_manager.list.return_value = []
    mock_manager_class.return_value = mock_manager

    result = runner.invoke(cli.app, ["list"])

    assert result.exit_code == 0
    assert "No containers found" in result.output


@patch("src.cli.ContainerManager")
def test_should_display_containers_when_list_has_items(mock_manager_class, cli, runner):
    container1 = Container(
        id="abc123",
        name="test1",
        command=["echo", "hello"],
        root_fs="/tmp/test1",
        hostname="test1",
        memory_limit=250000000,
        state=State.RUNNING,
        process_id=12345,
    )
    container2 = Container(
        id="def456",
        name="test2",
        command=["sleep", "infinity"],
        root_fs="/tmp/test2",
        hostname="test2",
        memory_limit=250000000,
        state=State.CREATED,
    )

    mock_manager = Mock()
    mock_manager.list.return_value = [container1, container2]
    mock_manager_class.return_value = mock_manager

    result = runner.invoke(cli.app, ["list"])

    assert result.exit_code == 0
    assert "abc123" in result.output
    assert "def456" in result.output
    assert "test1" in result.output
    assert "test2" in result.output


@patch("src.cli.ContainerManager")
def test_should_filter_by_state_when_state_provided(mock_manager_class, cli, runner):
    mock_manager = Mock()
    mock_manager.list.return_value = []
    mock_manager_class.return_value = mock_manager

    result = runner.invoke(cli.app, ["list", "--state", "running"])

    assert result.exit_code == 0
    mock_manager.list.assert_called_once_with(State.RUNNING)


def test_should_fail_when_invalid_state_provided(cli, runner):
    result = runner.invoke(cli.app, ["list", "--state", "invalid"])

    assert result.exit_code == 1
    assert "Invalid state" in result.output


@patch("src.cli.os.geteuid")
@patch("src.cli.ContainerManager")
def test_should_start_container_when_valid_id(
    mock_manager_class, mock_geteuid, cli, runner
):
    mock_geteuid.return_value = 0
    mock_manager = Mock()
    mock_manager_class.return_value = mock_manager

    result = runner.invoke(cli.app, ["start", "test123"])

    assert result.exit_code == 0
    assert "started successfully" in result.output
    mock_manager.start.assert_called_once_with("test123")


@patch("src.cli.os.geteuid")
@patch("src.cli.ContainerManager")
def test_should_fail_when_starting_nonexistent(
    mock_manager_class, mock_geteuid, cli, runner
):
    mock_geteuid.return_value = 0
    mock_manager = Mock()
    mock_manager.start.side_effect = ValueError("Container not found")
    mock_manager_class.return_value = mock_manager

    result = runner.invoke(cli.app, ["start", "nonexistent"])

    assert result.exit_code == 1
    assert "Container not found" in result.output


@patch("src.cli.os.geteuid")
@patch("src.cli.ContainerManager")
def test_should_handle_error_when_start_fails(
    mock_manager_class, mock_geteuid, cli, runner
):
    mock_geteuid.return_value = 0
    mock_manager = Mock()
    mock_manager.start.side_effect = Exception("Some error")
    mock_manager_class.return_value = mock_manager

    result = runner.invoke(cli.app, ["start", "test123"])

    assert result.exit_code == 1
    assert "Failed to start container" in result.output


@patch("src.cli.os.geteuid")
@patch("src.cli.ContainerManager")
def test_should_stop_container_when_running(
    mock_manager_class, mock_geteuid, cli, runner
):
    mock_geteuid.return_value = 0
    mock_manager = Mock()
    mock_manager_class.return_value = mock_manager

    result = runner.invoke(cli.app, ["stop", "test123"])

    assert result.exit_code == 0
    assert "stopped successfully" in result.output
    mock_manager.stop.assert_called_once_with("test123")


@patch("src.cli.os.geteuid")
@patch("src.cli.ContainerManager")
def test_should_fail_when_stopping_non_running(
    mock_manager_class, mock_geteuid, cli, runner
):
    mock_geteuid.return_value = 0
    mock_manager = Mock()
    mock_manager.stop.side_effect = ValueError("Container not running")
    mock_manager_class.return_value = mock_manager

    result = runner.invoke(cli.app, ["stop", "test123"])

    assert result.exit_code == 1
    assert "Container not running" in result.output


@patch("src.cli.os.geteuid")
@patch("src.cli.ContainerManager")
def test_should_remove_container_when_not_running(
    mock_manager_class, mock_geteuid, cli, runner
):
    mock_geteuid.return_value = 0
    mock_manager = Mock()
    mock_manager_class.return_value = mock_manager

    result = runner.invoke(cli.app, ["rm", "test123"])

    assert result.exit_code == 0
    assert "removed successfully" in result.output
    mock_manager.remove.assert_called_once_with("test123")


@patch("src.cli.os.geteuid")
@patch("src.cli.ContainerManager")
def test_should_fail_when_removing_running(
    mock_manager_class, mock_geteuid, cli, runner
):
    mock_geteuid.return_value = 0
    mock_manager = Mock()
    mock_manager.remove.side_effect = ValueError("Cannot remove running container")
    mock_manager_class.return_value = mock_manager

    result = runner.invoke(cli.app, ["rm", "test123"])

    assert result.exit_code == 1
    assert "Cannot remove running container" in result.output


@patch("src.cli.os.geteuid")
@patch("src.cli.ContainerManager")
def test_should_create_and_start_when_run_used(
    mock_manager_class, mock_geteuid, cli, runner
):
    mock_geteuid.return_value = 0
    mock_manager = Mock()
    mock_manager.create.return_value = "test123"
    mock_manager_class.return_value = mock_manager

    result = runner.invoke(cli.app, ["run", "--name", "test-run", "echo", "hello"])

    assert result.exit_code == 0
    assert "test123" in result.output
    assert "started successfully" in result.output
    mock_manager.create.assert_called_once_with("test-run", ["echo", "hello"])
    mock_manager.start.assert_called_once_with("test123")


@patch("src.cli.os.geteuid")
@patch("src.cli.ContainerManager")
def test_should_fail_run_when_start_fails(
    mock_manager_class, mock_geteuid, cli, runner
):
    mock_geteuid.return_value = 0
    mock_manager = Mock()
    mock_manager.create.return_value = "test123"
    mock_manager.start.side_effect = Exception("Start failed")
    mock_manager_class.return_value = mock_manager

    result = runner.invoke(cli.app, ["run", "--name", "test-run", "echo", "hello"])

    assert result.exit_code == 1
    assert "Failed to start container" in result.output


@patch("src.cli.os.geteuid")
def test_should_raise_typer_exit_when_not_root(mock_geteuid, cli):
    mock_geteuid.return_value = 1000

    with pytest.raises(typer.Exit):
        cli._check_root()


@patch("src.cli.os.geteuid")
def test_should_not_raise_when_user_is_root(mock_geteuid, cli):
    mock_geteuid.return_value = 0

    # Should not raise any exception
    cli._check_root()


@patch("src.cli.ContainerManager")
def test_should_truncate_long_commands_in_list(mock_manager_class, cli, runner):
    container = Container(
        id="abc123",
        name="test",
        command=["echo", "very", "long", "command", "with", "many", "arguments"],
        root_fs="/tmp/test",
        hostname="test",
        memory_limit=250000000,
        state=State.CREATED,
    )

    mock_manager = Mock()
    mock_manager.list.return_value = [container]
    mock_manager_class.return_value = mock_manager

    result = runner.invoke(cli.app, ["list"])

    assert result.exit_code == 0
    assert "echo very long..." in result.output


@patch("src.cli.ContainerManager")
def test_should_show_pid_for_running_containers(mock_manager_class, cli, runner):
    containers = [
        Container(
            id="run123",
            name="running-container",
            command=["sleep", "1000"],
            root_fs="/tmp/run",
            hostname="run",
            memory_limit=250000000,
            state=State.RUNNING,
            process_id=12345,
        ),
        Container(
            id="exit123",
            name="exited-container",
            command=["echo", "done"],
            root_fs="/tmp/exit",
            hostname="exit",
            memory_limit=250000000,
            state=State.EXITED,
            exit_code=0,
        ),
        Container(
            id="new123",
            name="created-container",
            command=["echo", "new"],
            root_fs="/tmp/new",
            hostname="new",
            memory_limit=250000000,
            state=State.CREATED,
        ),
    ]

    mock_manager = Mock()
    mock_manager.list.return_value = containers
    mock_manager_class.return_value = mock_manager

    result = runner.invoke(cli.app, ["list"])

    assert result.exit_code == 0
    # Verify PIDs are displayed correctly
    assert "12345" in result.output  # Running container has PID
    assert result.output.count("-") >= 2  # Non-running containers show "-" for PID


@patch("src.cli.os.geteuid")
@patch("src.cli.ContainerManager")
def test_should_complete_full_container_lifecycle(mock_manager_class, mock_geteuid):
    mock_geteuid.return_value = 0
    mock_manager = Mock()
    mock_manager.create.return_value = "test123"
    mock_manager.list.return_value = []
    mock_manager_class.return_value = mock_manager

    cli = MiniConCLI()
    runner = CliRunner()

    result = runner.invoke(
        cli.app, ["create", "--name", "lifecycle-test", "echo", "hello"]
    )
    assert result.exit_code == 0
    assert "test123" in result.output

    result = runner.invoke(cli.app, ["start", "test123"])
    assert result.exit_code == 0

    result = runner.invoke(cli.app, ["stop", "test123"])
    assert result.exit_code == 0

    result = runner.invoke(cli.app, ["rm", "test123"])
    assert result.exit_code == 0

    mock_manager.create.assert_called_once()
    mock_manager.start.assert_called_once()
    mock_manager.stop.assert_called_once()
    mock_manager.remove.assert_called_once()
