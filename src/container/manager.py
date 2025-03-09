"""Container manager."""

from src.container.registry import ContainerRegistry


class ContainerManager:
    """A class responsible for managing containers.

    The ContainerManager class provides methods for creating, starting,
    stopping, removing, and listing containers.
    It uses a ContainerRegistry instance to store and retrieve container
    information.

    Attributes:
        registry (ContainerRegistry): The registry used to store and retrieve
            container information.
    """

    def __init__(self) -> None:
        """Initialize a ContainerManager instance.

        This method initializes the container manager by creating an instance
        of the ContainerRegistry class.
        """
        self.registry = ContainerRegistry()

    def create(self) -> None:
        """Create a new container.

        This method creates a new container and adds it to the registry.
        """
        pass

    def start(self, container_id: str) -> None:
        """Start a container.

        This method starts a container by its ID, transitioning it to the running state.
        It retrieves the container from the registry and updates its state.

        Args:
            container_id: The unique identifier of the container to start.
        """
        pass

    def stop(self, container_id: str) -> None:
        """Stop a container.

        This method stops a container by its ID, transitioning it to the exited state.
        It retrieves the container from the registry and updates its state.

        Args:
            container_id: The unique identifier of the container to stop.
        """
        pass

    def remove(self, container_id: str) -> None:
        """Remove a container from the registry.

        This method removes a container from the registry by its ID. It ensures that
        the container and its associated metadata are deleted from the registry.

        Args:
            container_id: The unique identifier of the container to remove.
        """
        pass

    def list(self) -> None:
        """List all containers in the registry.

        This method retrieves all containers currently stored in the registry
        and returns them as a list.

        Returns:
            A list of all container instances in the registry.
        """
        pass
