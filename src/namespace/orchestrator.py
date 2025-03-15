"""Namespace orchestrator for MiniCon."""

import logging
import os
import signal
import time
from typing import List, Optional, Tuple

from src.namespace.handlers.mount_namespace import MountNamespaceHandler
from src.namespace.handlers.pid_namespace import PidNamespaceHandler
from src.namespace.handlers.user_namespace import UserNamespaceHandler
from src.namespace.handlers.uts_namespace import UtsNamespaceHandler

logger = logging.getLogger(__name__)


class NamespaceOrchestrator:
    """Orchestrates the creation and configuration of a container.

    This class provides a high-level interface for managing the creation and
    execution of a container. It abstracts away the low-level details of
    setting up namespace isolations, configuring resource limits,
    and handling container process lifecycle events.

    Attributes:
        _pid_handler (PidNamespaceHandler): A handler for managing PID
            namespace isolation.
        _mount_handler (MountNamespaceHandler): A handler for managing mount
            namespace isolation.
        _uts_handler (UtsNamespaceHandler): A handler for managing UTS
            namespace isolation.
        _user_handler (UserNamespaceHandler): A handler for managing user
            namespace isolation.
        _root_fs (str): The root filesystem for the container.
        _host_name (str): The hostname for the container.
        _command (list[str]): The command to execute in the container.
        _memory_limit (int): The memory limit for the container.
        _container_pid (int): The PID of the container process.
        _exit_code (int): The exit code of the container process.
    """

    def __init__(self) -> None:
        """Initialize the namespace orchestrator.

        This initializes the namespace handlers for PID, mount, UTS, and user
        namespaces. It also initializes the container metadata that is
        associated with the namespace setup.

        Args:
            None

        Returns:
            None
        """
        self._pid_handler = PidNamespaceHandler()
        self._mount_handler = MountNamespaceHandler()
        self._uts_handler = UtsNamespaceHandler()
        self._user_handler = UserNamespaceHandler()

        self._root_fs: Optional[str] = None
        self._host_name: Optional[str] = None
        self._command: Optional[list[str]] = None
        self._memory_limit: Optional[int] = None

        self._container_pid: Optional[int] = None
        self._exit_code: Optional[int] = None

    def configure(
        self,
        root_fs: str,
        hostname: str,
        command: List[str],
        memory_limit: int,
        uid_map: List[Tuple[int, int, int]],
        gid_map: List[Tuple[int, int, int]],
    ) -> None:
        """Configure the container with the specified settings.

        This method sets up the root filesystem, hostname, command to execute,
        memory limit, and UID/GID mappings for the container. These configurations
        are essential for the proper isolation and functioning of the container.

        Args:
            root_fs: The path to the root filesystem for the container.
            hostname: The hostname to assign to the container.
            command: A list of command-line arguments to execute in the container.
            memory_limit: The memory limit in bytes for the container.
            uid_map: A list of tuples representing UID mappings
                (inside_uid, outside_uid, count)
            gid_map: A list of tuples representing GID mappings
                (inside_gid, outside_gid, count)

        Returns:
            None
        """
        self._root_fs = root_fs
        self._hostname = hostname
        self._command = command
        self._memory_limit = memory_limit

        self._mount_handler.set_root_fs(self._root_fs)
        self._uts_handler.set_hostname(self._hostname)

        for inside_uid, outside_uid, count in uid_map:
            self._user_handler.add_uid_mapping(inside_uid, outside_uid, count)

        for inside_gid, outside_gid, count in gid_map:
            self._user_handler.add_gid_mapping(inside_gid, outside_gid, count)

        if uid_map and gid_map:
            inside_uid, _, _ = uid_map[0]
            inside_gid, _, _ = gid_map[0]
            self._user_handler.set_user(inside_uid, inside_gid)

        logger.info(
            f"Configured container with root_fs: {self._root_fs}, hostname: "
            f"{self._hostname}, command: {self._command}, memory_limit: "
            f"{self._memory_limit}"
        )

    def set_cgroup_settings(self, memory_limit: int, cpu_shares: int = 1024) -> None:
        """Set cgroup settings for memory and CPU resources.

        This method sets the memory limit and CPU shares for the container
        process. It uses the cgroups kernel feature to enforce these limits.

        Args:
            memory_limit: The memory limit in bytes for the container process.
            cpu_shares: The relative CPU share for the container process.
                    Default is 1024, which means 100% of one CPU core.

        Returns:
            None
        """
        self._memory_limit = memory_limit
        self._cpu_shares = cpu_shares

        logger.info(
            f"Set cgroup settings with memory_limit: {self._memory_limit}, "
            f"cpu_shares: {self._cpu_shares}"
        )

    def setup_namespaces(self) -> None:
        """Set up the namespaces for the container.

        This method sets up the necessary namespaces (mount, UTS, PID, user)
        for the container. It calls the setup method of each namespace handler
        to perform the necessary setup.

        Returns:
            None
        """
        logger.info("Setting up namespaces...")

        try:
            self._user_handler.setup()
            self._mount_handler.setup()
            self._uts_handler.setup()
            self._pid_handler.setup()
        except OSError as e:
            logger.error(f"Failed to setup namespaces: {e}")
            raise RuntimeError(f"Failed to setup namespaces: {e}")
        except Exception as e:
            logger.error(f"Unexpected error occurred while setting up namespaces: {e}")
            raise

        logger.info("Namespaces setup completed successfully.")

    def create_container_process(self) -> int:
        """Create the container process and return its PID.

        This method creates the container process in the new namespaces
        by forking a child process and setting up the required isolation.
        The child process will run the container command in the isolated
        environment.

        Returns:
            The PID of the created container process.
        """
        if not self._command:
            raise ValueError("Command not set for container. Call configure() first.")

        try:
            self.setup_namespaces()
            self._container_pid = self._pid_handler.fork_in_new_namespace(
                self._container_entry_point
            )
            logger.info(f"Container process created with PID: {self._container_pid}")

            self._setup_cgroups()
        except Exception as e:
            logger.error(f"Failed to create container process: {e}")
            raise RuntimeError(f"Failed to create container process: {e}")

        return self._container_pid

    def wait_for_exit(self) -> int:
        """Wait for the container process to exit.

        This method waits for the container process to complete its
        execution and returns the exit code of the process.

        Returns:
            The exit code of the container process.
        """
        if not self._container_pid:
            raise ValueError("Container process not created yet.")

        logger.info(f"Waiting for container process {self._container_pid} to exit...")

        _, status = os.waitpid(self._container_pid, 0)

        if os.WIFEXITED(status):
            exit_code = os.WEXITSTATUS(status)
        else:
            exit_code = -1

        self._exit_code = exit_code
        logger.info(
            f"Container process {self._container_pid} exited with exit code {exit_code}"
        )

        self.cleanup_resources()

        return exit_code

    def terminate(self) -> None:
        """Terminate the container process.

        This method is responsible for terminating the container process.
        It sends SIGTERM to the process and waits for it to exit.
        """
        if not self._container_pid:
            raise ValueError("Container process not created yet.")

        logger.info(f"Terminating container process {self._container_pid}...")

        try:
            os.kill(self._container_pid, signal.SIGTERM)

            try:
                _, status = os.waitpid(self._container_pid, os.WNOHANG)
                if not os.WIFSIGNALED(status) and not os.WIFEXITED(status):
                    timeout = 5
                    time.sleep(timeout)

                    _, status = os.waitpid(self._container_pid, os.WNOHANG)
                    if not os.WIFSIGNALED(status) and not os.WIFEXITED(status):
                        logger.warning(
                            f"Container process {self._container_pid} did not "
                            f"terminate after {timeout} seconds, sending SIGKILL"
                        )
                        os.kill(self._container_pid, signal.SIGKILL)
            except ChildProcessError:
                logger.info(
                    f"Container process {self._container_pid} already terminated"
                )
                pass

            if os.WIFEXITED(status):
                self._exit_code = os.WEXITSTATUS(status)
            else:
                self._exit_code = -1

            logger.info(
                f"Container process {self._container_pid} "
                f"terminated with exit code {self._exit_code}"
            )
        except ProcessLookupError as e:
            logger.warning(
                f"Container process {self._container_pid} already terminated: {e}"
            )
        except Exception as e:
            logger.error(f"Failed to terminate container process: {e}")

        self.cleanup_resources()

    def cleanup_resources(self) -> None:
        """Clean up resources allocated for the container.

        This method removes the cgroup created for the container
        and resets the internal state.
        """
        if not self._container_pid:
            return

        logger.info(f"Cleaning up resources for container {self._container_pid}")

        cgroup_path = f"/sys/fs/cgroup/minicon_{self._container_pid}"
        if os.path.exists(cgroup_path):
            try:
                if os.path.exists(f"{cgroup_path}/cgroup.procs"):
                    with open(f"{cgroup_path}/cgroup.procs", "r") as f:
                        procs = f.read().strip().split("\n")

                    if procs and procs[0]:
                        with open("/sys/fs/cgroup/cgroup.procs", "w") as f:
                            for proc in procs:
                                try:
                                    f.write(proc)
                                except Exception:
                                    pass

                os.rmdir(cgroup_path)
                logger.info(f"Removed cgroup {cgroup_path}")
            except Exception as e:
                logger.error(f"Error removing cgroup: {e}")

        self._container_pid = None

    def _apply_isolation(self) -> None:
        """Apply namespace isolation in the child process.

        This method is called in the container process to apply the
        namespace isolation such as changing root, mounting /proc,
        and setting the hostname.
        """
        logger.info("Applying namespace isolation in container process")

        if self._root_fs:
            logger.info(f"Changing root to {self._root_fs}")
            self._mount_handler.apply_mount_isolation()

        if self._hostname:
            logger.info(f"Setting hostname to {self._hostname}")
            self._uts_handler.apply_uts_isolation()

        if (
            self._user_handler._uid_mappings
            and self._user_handler._gid_mappings
            and self._user_handler.child_pid
        ):
            logger.info("Applying user namespace isolation")
            self._user_handler.apply_user_isolation()

        logger.info("Namespace isolation applied successfully")

    def _setup_cgroups(self) -> None:
        """Set up cgroups for the container process.

        This method creates the necessary cgroup for the container process
        and sets memory limits using cgroups v2.
        """
        if not self._container_pid:
            raise ValueError("Container process not created yet.")

        if not self._memory_limit:
            logger.info("No memory limit set, skipping cgroup setup")
            return

        logger.info(f"Setting up cgroups v2 for container PID {self._container_pid}")

        cgroup_path = f"/sys/fs/cgroup/minicon_{self._container_pid}"
        try:
            os.makedirs(cgroup_path, exist_ok=True)

            parent_controllers_path = "/sys/fs/cgroup/cgroup.subtree_control"
            with open(parent_controllers_path, "r") as f:
                current_controllers = f.read()

            if "+memory" not in current_controllers:
                try:
                    with open(parent_controllers_path, "w") as f:
                        f.write("+memory")
                    logger.info("Enabled memory controller in parent cgroup")
                except Exception as e:
                    logger.warning(f"Could not enable memory controller: {e}")

            with open(f"{cgroup_path}/memory.max", "w") as f:
                f.write(str(self._memory_limit))

            with open(f"{cgroup_path}/cgroup.procs", "w") as f:
                f.write(str(self._container_pid))

            logger.info(
                f"Container process {self._container_pid} added to "
                f"cgroup with memory limit {self._memory_limit} bytes"
            )
        except Exception as e:
            logger.error(f"Failed to set up cgroups: {e}")

    def _container_entry_point(self) -> int:
        """Entry point for the container process.

        This method is executed in the child process after fork. It:
        1. Applies namespace isolation (chroot, hostname, etc.)
        2. Drops privileges if necessary
        3. Executes the container command

        Returns:
            The exit code of the container process.
        """
        if not self._command:
            raise ValueError("Command not set for container. Call configure() first.")

        try:
            self._apply_isolation()

            if self._user_handler.user_id is not None:
                self._user_handler.drop_privileges()

            logger.info(f"Executing container command: {self._command}")

            os.execvp(self._command[0], self._command)

            logger.error("Failed to execute container command")
            return 1
        except Exception as e:
            logger.error(f"Error in container process: {e}")
            return 1

    def _handle_child_exit(self, status: int) -> None:
        """Handle the exit of the child process.

        This method extracts the exit code from the status and
        updates the internal state.

        Args:
            status: The exit status of the child process.
        """
        if os.WIFEXITED(status):
            self._exit_code = os.WEXITSTATUS(status)
            logger.info(f"Container process exited with code {self._exit_code}")
        elif os.WIFSIGNALED(status):
            signal_num = os.WTERMSIG(status)
            self._exit_code = 128 + signal_num
            logger.info(f"Container process terminated by signal {signal_num}")
        else:
            self._exit_code = -1
            logger.warning("Container process exited abnormally")
