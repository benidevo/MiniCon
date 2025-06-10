"""Tests for the NamespaceOrchestrator class."""

import os
import signal
from unittest.mock import MagicMock, patch

import pytest


def test_should_configure_handlers_correctly(orchestrator):
    root_fs = "/var/lib/minicon/rootfs/test"
    hostname = "test-container"
    command = ["python", "-m", "http.server"]
    memory_limit = 100 * 1024 * 1024
    uid_map = [(0, 1000, 1)]
    gid_map = [(0, 1000, 1)]

    orchestrator.configure(
        root_fs=root_fs,
        hostname=hostname,
        command=command,
        memory_limit=memory_limit,
        uid_map=uid_map,
        gid_map=gid_map,
    )

    assert orchestrator._mount_handler.root_fs == root_fs
    assert orchestrator._uts_handler._hostname == hostname
    assert (0, 1000, 1) in orchestrator._user_handler._uid_mappings
    assert (0, 1000, 1) in orchestrator._user_handler._gid_mappings


def test_should_setup_all_namespaces(configured_orchestrator):
    with (
        patch.object(configured_orchestrator._user_handler, "setup") as mock_user_setup,
        patch.object(
            configured_orchestrator._mount_handler, "setup"
        ) as mock_mount_setup,
        patch.object(configured_orchestrator._uts_handler, "setup") as mock_uts_setup,
        patch.object(configured_orchestrator._pid_handler, "setup") as mock_pid_setup,
    ):
        configured_orchestrator.setup_namespaces()

        mock_user_setup.assert_called_once()
        mock_mount_setup.assert_called_once()
        mock_uts_setup.assert_called_once()
        mock_pid_setup.assert_called_once()


def test_should_create_container_process_with_proper_isolation(configured_orchestrator):
    with (
        patch.object(
            configured_orchestrator, "setup_namespaces"
        ) as mock_setup_namespaces,
        patch.object(
            configured_orchestrator._pid_handler, "fork_in_new_namespace_sync"
        ) as mock_fork_sync,
        patch.object(
            configured_orchestrator, "_pre_setup_cgroups"
        ) as mock_pre_setup_cgroups,
        patch.object(
            configured_orchestrator, "_apply_process_to_cgroup"
        ) as mock_apply_process_to_cgroup,
        patch("os.pipe", return_value=(3, 4)),
        patch("os.write"),
        patch("os.close"),
    ):
        mock_fork_sync.return_value = 12345

        pid = configured_orchestrator.create_container_process()

        assert pid == 12345
        mock_setup_namespaces.assert_called_once()
        mock_fork_sync.assert_called_once_with(
            configured_orchestrator._container_entry_point, 3, 4
        )
        mock_pre_setup_cgroups.assert_called_once()
        mock_apply_process_to_cgroup.assert_called_once()


def test_should_apply_isolation_in_container_process(configured_orchestrator):
    with (
        patch.object(
            configured_orchestrator._mount_handler, "apply_mount_isolation"
        ) as mock_mount,
        patch.object(
            configured_orchestrator._uts_handler, "apply_uts_isolation"
        ) as mock_uts,
    ):
        configured_orchestrator._apply_isolation()

        mock_mount.assert_called_once()
        mock_uts.assert_called_once()


def test_should_execute_command_in_container_entry_point(configured_orchestrator):
    with (
        patch.object(
            configured_orchestrator, "_apply_isolation"
        ) as mock_apply_isolation,
        patch("os.execvp") as mock_execvp,
        patch.object(configured_orchestrator._user_handler, "drop_privileges"),
    ):
        configured_orchestrator._container_entry_point()

        mock_apply_isolation.assert_called_once()
        mock_execvp.assert_called_once_with("python", ["python", "-m", "http.server"])


def test_should_handle_container_lifecycle(configured_orchestrator):
    configured_orchestrator._container_pid = 12345

    with (
        patch("os.waitpid") as mock_waitpid,
        patch.object(os, "WIFEXITED", return_value=True),
        patch.object(os, "WEXITSTATUS", return_value=0),
        patch.object(configured_orchestrator, "cleanup_resources") as mock_cleanup,
    ):
        mock_waitpid.return_value = (12345, 0)

        exit_code = configured_orchestrator.wait_for_exit()

        assert exit_code == 0
        mock_waitpid.assert_called_once_with(12345, 0)
        mock_cleanup.assert_called_once()

    configured_orchestrator._container_pid = 12345

    with (
        patch("os.kill") as mock_kill,
        patch("os.waitpid") as mock_waitpid,
        patch.object(os, "WIFEXITED", return_value=True),
        patch.object(os, "WEXITSTATUS", return_value=0),
        patch.object(configured_orchestrator, "cleanup_resources") as mock_cleanup,
    ):
        mock_waitpid.return_value = (12345, 0)

        configured_orchestrator.terminate()

        mock_kill.assert_called_once_with(12345, signal.SIGTERM)
        mock_cleanup.assert_called_once()


def test_should_cleanup_resources(configured_orchestrator):
    configured_orchestrator._container_pid = 12345
    cgroup_path = f"/sys/fs/cgroup/minicon_{12345}"

    with (
        patch("os.path.exists", return_value=True),
        patch("builtins.open", MagicMock()),
        patch("os.rmdir") as mock_rmdir,
    ):
        configured_orchestrator.cleanup_resources()

        mock_rmdir.assert_called_once_with(cgroup_path)
        assert configured_orchestrator._container_pid is None


def test_should_validate_container_command(orchestrator):
    with pytest.raises(ValueError, match="Command not set for container"):
        orchestrator.create_container_process()

    orchestrator._command = None
    with pytest.raises(ValueError, match="Command not set for container"):
        orchestrator._container_entry_point()
