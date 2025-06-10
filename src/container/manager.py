"""Container manager."""

import logging
import os
import threading
import uuid
from typing import Optional

from src.constants import (
    ESSENTIAL_DIRECTORIES,
    MINICON_BASE_DIR,
    MINICON_BASE_IMAGE,
    MINICON_MEMORY_LIMIT,
    MINICON_ROOTFS_DIR,
)
from src.container.model import Container, State
from src.container.registry import ContainerRegistry
from src.namespace.orchestrator import NamespaceOrchestrator
from src.utils.security import (
    SecurityError,
    safe_copy_directory,
    safe_extract_tar,
    validate_command,
    validate_container_name,
)

logger = logging.getLogger(__name__)


class ContainerManager:
    """Container manager for creating, starting, and managing containers.

    This class provides methods to create, start, stop, and remove containers.
    It uses the ContainerRegistry to persist container metadata and the
    NamespaceOrchestrator to manage container namespaces and processes.

    Attributes:
        registry (ContainerRegistry): Registry for persisting container metadata.
        _orchestrators (dict[str, NamespaceOrchestrator]): Dictionary of orchestrators
            for running containers, keyed by container ID.
        _orchestrator_class (type[NamespaceOrchestrator]): Class used to create
            orchestrator instances.
        _container_class (type[Container]): Class used to create container instances.
    """

    _orchestrator_class: type[NamespaceOrchestrator] = NamespaceOrchestrator
    _container_class: type[Container] = Container

    def __init__(self) -> None:
        """Initialize the container manager.

        This constructor initializes the container manager with a registry for
        persisting container metadata and a dictionary to track orchestrators
        for running containers. It also attempts to recover any containers that
        were previously in the running state.

        The container manager serves as the main interface for creating, starting,
        stopping, and removing containers in the system.
        """
        self.registry: ContainerRegistry = ContainerRegistry()
        self._orchestrators: dict[str, NamespaceOrchestrator] = {}
        self._recover_running_containers()

    def _recover_running_containers(self) -> None:
        running_containers = self.registry.get_all_containers(State.RUNNING)
        for container in running_containers:
            if container.process_id and self._is_process_running(container.process_id):
                orchestrator = self._orchestrator_class()
                orchestrator._container_pid = container.process_id
                self._orchestrators[container.id] = orchestrator

                try:
                    monitor_thread = threading.Thread(
                        target=self._monitor_container,
                        args=(container.id,),
                        daemon=True,
                    )
                    monitor_thread.start()
                except Exception as e:
                    logger.warning(
                        f"Failed to start monitoring thread for container "
                        f"{container.id}: {e}"
                    )
                    # Mark as exited since we can't monitor it
                    self.registry.update_container_state(container.id, State.EXITED)
                    self._orchestrators.pop(container.id, None)
            else:
                # Process died, mark as exited
                self.registry.update_container_state(container.id, State.EXITED)
                self._orchestrators.pop(container.id, None)

    def _is_process_running(self, process_id: int) -> bool:
        try:
            os.kill(process_id, 0)
            return True
        except OSError:
            return False

    def create(
        self, name: str, command: list[str], memory_limit: int = MINICON_MEMORY_LIMIT
    ) -> str:
        """Create a new container.

        This method creates a new container with the specified name,
        command, and memory limit. It generates a unique ID for the container,
        prepares the root filesystem, and registers the container in the registry.

        Args:
            name: The human-readable name for the container.
            command: A list of strings representing the command and its
                arguments to run in the container.
            memory_limit: The memory limit in bytes for the container.
                Defaults to MINICON_MEMORY_LIMIT.

        Returns:
            The unique identifier (ID) of the created container.

        Raises:
            ValueError: If name or command validation fails.
            SecurityError: If security validation fails.
        """
        if not validate_container_name(name):
            raise ValueError(f"Invalid container name: {name}")

        if not validate_command(command):
            raise ValueError(f"Invalid or dangerous command: {command}")

        container_id = str(uuid.uuid4())[:8]
        root_fs_path = self._prepare_root_fs(container_id)
        container = self._container_class(
            id=container_id,
            name=name,
            command=command,
            hostname=name,
            memory_limit=memory_limit,
            root_fs=root_fs_path,
        )
        self.registry.save_container(container)
        return container_id

    def start(self, container_id: str) -> None:
        """Start a container.

        This method starts a container by its ID, transitioning it to the
        running state. It retrieves the container from the registry,
        configures a namespace orchestrator, and creates the container process.
        It also starts a monitoring thread to track the container's lifecycle.

        Args:
            container_id: The unique identifier of the container to start.

        Raises:
            ValueError: If the container is not found or not in the created state.
            RuntimeError: If the container fails to start due to configuration or
                resource allocation issues.
        """
        container = self.registry.get_container(container_id)
        if not container:
            raise ValueError(f"Container {container_id} not found")
        if container.state != State.CREATED:
            raise ValueError(f"Container {container_id} is not in the created state")

        orchestrator = self._orchestrator_class()
        try:
            orchestrator.configure(
                root_fs=container.root_fs,
                hostname=container.hostname,
                command=container.command,
                memory_limit=container.memory_limit,
                uid_map=[(0, os.getuid(), 1)],
                gid_map=[(0, os.getgid(), 1)],
            )
            orchestrator.set_cgroup_settings(
                memory_limit=container.memory_limit,
            )
            pid = orchestrator.create_container_process()
            kwargs = {"process_id": pid}
            self.registry.update_container_state(container_id, State.RUNNING, **kwargs)
            self._orchestrators[container_id] = orchestrator
        except Exception as e:
            logger.error(f"Failed to start container {container_id}: {e}")
            orchestrator.cleanup_resources()
            raise RuntimeError(f"Failed to start container {container_id}: {e}") from e

        try:
            monitor_thread = threading.Thread(
                target=self._monitor_container,
                args=(container_id,),
                daemon=True,
            )
            monitor_thread.start()
        except RuntimeError as e:
            logger.warning(f"Could not start monitoring thread: {e}")

    def _monitor_container(self, container_id: str) -> None:
        orchestrator = self._orchestrators.get(container_id)
        if not orchestrator:
            return

        try:
            exit_code = orchestrator.wait_for_exit()
            self.registry.update_container_state(
                container_id, State.EXITED, exit_code=exit_code
            )
        except (OSError, ChildProcessError) as e:
            logger.warning(f"Failed to monitor container {container_id}: {e}")
            # Process might have already exited, mark as exited with unknown code
            self.registry.update_container_state(
                container_id, State.EXITED, exit_code=-1
            )
        except Exception as e:
            logger.error(f"Unexpected error monitoring container {container_id}: {e}")
            self.registry.update_container_state(
                container_id, State.EXITED, exit_code=-1
            )
        finally:
            self._orchestrators.pop(container_id, None)

    def stop(self, container_id: str) -> bool:
        """Stop a container.

        This method stops a running container by its ID, transitioning it to
        the exited state.
        It retrieves the container from the registry, gets the associated orchestrator,
        and terminates the container process.

        Args:
            container_id: The unique identifier of the container to stop.

        Returns:
            bool: True if the container was successfully stopped.

        Raises:
            ValueError: If the container is not found, not in the running state,
                or if the orchestrator for the container is not found.
        """
        container = self.registry.get_container(container_id)
        if not container:
            raise ValueError(f"Container {container_id} not found")
        if container.state != State.RUNNING:
            raise ValueError(f"Container {container_id} is not in the running state")

        orchestrator = self._orchestrators.get(container_id)
        if not orchestrator:
            raise ValueError(f"Orchestrator for container {container_id} not found")

        orchestrator.terminate()
        self.registry.update_container_state(container_id, State.EXITED)
        return True

    def remove(self, container_id: str) -> None:
        """Remove a container.

        This method removes a container from the registry and cleans
        up any associated resources.
        If the container is running, it will raise a ValueError.

        Args:
            container_id: The unique identifier of the container to remove.

        Raises:
            ValueError: If the container is not found or if it is still running.
        """
        container = self.registry.get_container(container_id)
        if not container:
            raise ValueError(f"Container {container_id} not found")

        if container.state == State.RUNNING:
            raise ValueError(
                f"Cannot remove running container {container_id}. Stop it first."
            )
        container = self.registry.get_container(container_id)
        if not container:
            raise ValueError(f"Container {container_id} not found")
        self.registry.remove_container(container_id)
        orchestrator = self._orchestrators.pop(container_id, None)
        if orchestrator:
            orchestrator.cleanup_resources()

    def list(self, state: Optional[State] = None) -> list[Container]:
        """List containers, optionally filtered by state.

        This method retrieves all containers from the registry, optionally filtered
        by their state. It returns a list of Container objects that match the
        specified criteria.

        Args:
            state: Optional state to filter containers by. If None, all containers
                are returned regardless of state.

        Returns:
            A list of Container objects, optionally filtered by state.
        """
        return self.registry.get_all_containers(state)

    def _prepare_root_fs(self, container_id: str) -> str:
        base_dir = MINICON_BASE_DIR
        base_image_path = MINICON_BASE_IMAGE
        root_fs_path = f"{MINICON_ROOTFS_DIR}/{container_id}"

        os.makedirs(base_dir, exist_ok=True)
        os.makedirs(root_fs_path, exist_ok=True)

        if os.path.exists(base_image_path):
            try:
                if os.path.isdir(base_image_path):
                    safe_copy_directory(base_image_path, root_fs_path)
                elif os.path.isfile(base_image_path) and base_image_path.endswith(
                    ".tar"
                ):
                    safe_extract_tar(base_image_path, root_fs_path)
            except SecurityError as e:
                logger.error(f"Security error preparing root filesystem: {e}")
                raise
            except Exception as e:
                logger.error(f"Failed to prepare base filesystem: {e}")
                # Continue with minimal filesystem creation
        else:
            logger.warning(
                f"Base image not found: {base_image_path}. Creating minimal filesystem."
            )

        for dir_name in ESSENTIAL_DIRECTORIES:
            os.makedirs(os.path.join(root_fs_path, dir_name), exist_ok=True)

        # Copy essential system binaries
        self._copy_essential_binaries(root_fs_path)

        hosts_file = os.path.join(root_fs_path, "etc/hosts")
        if not os.path.exists(hosts_file):
            with open(hosts_file, "w") as _file:
                _file.write("127.0.0.1 localhost\n")
                _file.write(f"127.0.0.1 {container_id}\n")

        return root_fs_path

    def _copy_essential_binaries(self, root_fs_path: str) -> None:
        """Copy essential system binaries and libraries to container filesystem."""
        import shutil

        # Copy shared libraries first
        self._copy_shared_libraries(root_fs_path)

        from ..constants import ESSENTIAL_BINARY_PATHS

        essential_binaries = ESSENTIAL_BINARY_PATHS

        bin_dir = os.path.join(root_fs_path, "bin")

        for binary_paths in essential_binaries:
            binary_copied = False
            for binary_path in binary_paths:
                if os.path.exists(binary_path):
                    try:
                        binary_name = os.path.basename(binary_path)
                        dest_path = os.path.join(bin_dir, binary_name)

                        # Copy binary if it doesn't exist
                        if not os.path.exists(dest_path):
                            shutil.copy2(binary_path, dest_path)
                            # Make executable
                            from src.constants import EXECUTABLE_PERMISSION

                            os.chmod(dest_path, EXECUTABLE_PERMISSION)
                            logger.info(f"Copied {binary_path} to container")
                            binary_copied = True
                            break
                    except Exception as e:
                        logger.warning(f"Failed to copy {binary_path}: {e}")
                        continue

            if not binary_copied:
                logger.warning(f"Could not find any of {binary_paths} to copy")

    def _copy_shared_libraries(self, root_fs_path: str) -> None:
        """Copy essential shared libraries to container filesystem."""
        import shutil

        from ..constants import CONTAINER_LIB_DIRS, ESSENTIAL_SYSTEM_LIBS

        # Create lib directories
        for lib_dir in CONTAINER_LIB_DIRS:
            os.makedirs(os.path.join(root_fs_path, lib_dir), exist_ok=True)

        # Essential libraries and their destination paths
        essential_libs = ESSENTIAL_SYSTEM_LIBS

        for src_path, dest_rel_path in essential_libs:
            if os.path.exists(src_path):
                try:
                    dest_path = os.path.join(root_fs_path, dest_rel_path)
                    dest_dir = os.path.dirname(dest_path)
                    os.makedirs(dest_dir, exist_ok=True)

                    if not os.path.exists(dest_path):
                        shutil.copy2(src_path, dest_path)
                        logger.info(f"Copied library {src_path} to container")
                except Exception as e:
                    logger.warning(f"Failed to copy library {src_path}: {e}")
