"""Container registry."""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from src.container.model import Container, State

logger = logging.getLogger(__name__)


class ContainerRegistry:
    """Manages a collection of containers, storing their metadata in a JSON file.

    The registry provides methods to load, save, retrieve, and update containers.
    It also handles serialization and deserialization of container data to and
    from the JSON file.

    Args:
        registry_file (str, optional): Path to the JSON file used to store
            container metadata. Defaults to"containers.json".

    Attributes:
        _registry_file (str): Path to the JSON file used to store container
            metadata.
        _containers (Dict[str, Container]): Dictionary of containers, keyed
            by container ID.
    """

    def __init__(self, registry_file: str = "containers.json"):
        """Initializes the container registry.

        Args:
            registry_file (str, optional): Path to the JSON file used to store
                container metadata. Defaults to"containers.json".
        """
        self._registry_file = registry_file
        self._containers: Dict[str, Container] = {}
        self.load_containers()

    def load_containers(self) -> None:
        """Loads container metadata from the registry file.

        If the file exists, its contents are deserialized and used to populate the
        `_containers` dictionary. If the file does not exist, a warning is logged.
        If an error occurs while loading the file, an error is logged and the
        exception is re-raised.
        """
        try:
            if os.path.exists(self._registry_file):
                with open(self._registry_file, "r") as _file:
                    data = json.load(_file)
                    self._containers = {
                        container_id: self._deserialize_container(container_data)
                        for container_id, container_data in data.items()
                    }
                    logger.info(
                        f"Loaded {len(self._containers)} containers from"
                        f"{self._registry_file}"
                    )
            else:
                logger.warning(f"Registry file {self._registry_file} not found")
        except Exception as e:
            logger.error(f"Failed to load containers from {self._registry_file}: {e}")

    def save_container(self, container: Container) -> None:
        """Saves a container to the registry.

        The container is stored in the registry dictionary by its ID and
        then the registry file is updated.

        Args:
            container: The container to save.
        """
        self._containers[container.id] = container
        self._save_to_file()

    def get_container(self, container_id: str) -> Optional[Container]:
        """Retrieve a container by its ID.

        Args:
            container_id: The unique identifier of the container to retrieve.

        Returns:
            The container with the specified ID, or None if no container with
            the given ID exists in the registry.
        """
        return self._containers.get(container_id)

    def get_all_containers(self) -> List[Container]:
        """Retrieve all containers in the registry.

        Returns:
            A list of all containers in the registry, or an empty list if
            there are no containers in the registry.
        """
        return list(self._containers.values())

    def update_container_state(
        self, container_id: str, new_state: State, **kwargs: Dict[str, Any]
    ) -> bool:
        """Updates a container's state and saves the registry.

        Args:
            container_id: The unique identifier of the container to update.
            new_state: The new state to set for the container.
            **kwargs: Additional keyword arguments to set on the container.

        Returns:
            True if the container was updated, False if no container with
                the given ID exists in the registry.
        """
        if container_id not in self._containers:
            return False

        container = self._containers[container_id]
        container.state = new_state

        for key, value in kwargs.items():
            if hasattr(container, key):
                setattr(container, key, value)

        self._save_to_file()
        return True

    def remove_container(self, container_id: str) -> bool:
        """Removes a container from the registry.

        Args:
            container_id: The unique identifier of the container to remove.

        Returns:
            True if the container was removed, False if no container with the
                given ID exists in the registry.
        """
        if container_id in self._containers:
            del self._containers[container_id]
            self._save_to_file()
            return True
        return False

    def _save_to_file(self) -> None:
        """Saves the container registry to a file.

        This method serializes the `_containers` dictionary to a JSON file
        atomically, first writing to a temporary file and then replacing the
        original file with the temporary file. If an error occurs during
        serialization or file writing, the original file is left intact and
        the exception is re-raised.
        """
        try:
            os.makedirs(os.path.dirname(self._registry_file), exist_ok=True)

            data = {
                container_id: self._serialize_container(container)
                for container_id, container in self._containers.items()
            }

            temp_file = f"{self._registry_file}.tmp"
            with open(temp_file, "w") as _file:
                json.dump(data, _file, indent=2)

            os.replace(temp_file, self._registry_file)
        except Exception as e:
            logger.error(f"Failed to save containers to {self._registry_file}: {e}")
            raise e

    def _serialize_container(self, container: Container) -> dict:  # type: ignore
        return container.to_dict()

    def _deserialize_container(self, container_data: dict) -> Container:
        return Container.from_dict(container_data)
