"""Container manager."""

import logging
import os
import threading
import uuid
from typing import Optional

from src.container.model import Container, State
from src.container.registry import ContainerRegistry
from src.namespace.orchestrator import NamespaceOrchestrator

logger = logging.getLogger(__name__)

DEFAULT_MEMORY_LIMIT = 250 * 1024 * 1024  # 250MB


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
                self.start(container.id)
            else:
                self.registry.update_container_state(container.id, State.EXITED)
                self._orchestrators.pop(container.id, None)

    def _is_process_running(self, process_id: int) -> bool:
        try:
            os.kill(process_id, 0)
            return True
        except OSError:
            return False

    def create(
        self, name: str, command: list[str], memory_limit: int = DEFAULT_MEMORY_LIMIT
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
                Defaults to DEFAULT_MEMORY_LIMIT.

        Returns:
            The unique identifier (ID) of the created container.
        """
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

        monitor_thread = threading.Thread(
            target=self._monitor_container,
            args=(container_id,),
            daemon=True,
        )
        monitor_thread.start()

    def _monitor_container(self, container_id: str) -> None:
        orchestrator = self._orchestrators.get(container_id)
        if not orchestrator:
            return

        exit_code = orchestrator.wait_for_exit()
        self.registry.update_container_state(
            container_id, State.EXITED, exit_code=exit_code
        )
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
        base_dir = "/var/lib/minicon"
        base_image_path = "/var/lib/minicon/base"
        root_fs_path = f"/var/lib/minicon/rootfs/{container_id}"

        os.makedirs(base_dir, exist_ok=True)
        os.makedirs(root_fs_path, exist_ok=True)

        os.makedirs(root_fs_path, exist_ok=True)
        if os.path.exists(base_image_path):
            if os.path.isdir(base_image_path):
                os.system(f"cp -a {base_image_path}/* {root_fs_path}/")
            elif os.path.isfile(base_image_path) and base_image_path.endswith(".tar"):
                os.system(f"tar -xf {base_image_path} -C {root_fs_path}")
        else:
            logger.warning(
                f"Base image not found: {base_image_path}. Creating minimal filesystem."
            )

        for dir_name in ["proc", "sys", "dev", "tmp", "etc", "bin", "lib", "home"]:
            os.makedirs(os.path.join(root_fs_path, dir_name), exist_ok=True)

        hosts_file = os.path.join(root_fs_path, "etc/hosts")
        if not os.path.exists(hosts_file):
            with open(hosts_file, "w") as _file:
                _file.write("127.0.0.1 localhost\n")
                _file.write(f"127.0.0.1 {container_id}\n")

        return root_fs_path
