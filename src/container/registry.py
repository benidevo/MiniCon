import json
import logging
import os
from typing import Dict, List, Optional

from container.model import Container, State

logger = logging.getLogger(__name__)

class ContainerRegistry:

    def __init__(self, registry_file: str = "containers.json"):
        self._registry_file = registry_file
        self._containers: Dict[str, Container] = {}
        self.load_containers()

    def load_containers(self):
       try:
            if os.path.exists(self._registry_file):
               with open(self._registry_file, "r") as _file:
                   data = json.load(_file)
                   self._containers = {
                       container_id: self._deserialize_container(container_data)
                       for container_id, container_data in data.items()
                   }
                   logger.info(f"Loaded {len(self._containers)} containers from {self._registry_file}")
            else:
                logger.warning(f"Registry file {self._registry_file} not found")
       except Exception as e:
           logger.error(f"Failed to load containers from {self._registry_file}: {e}")


    def save_container(self, container: Container) -> None:
        self._containers[container.id] = container
        self._save_to_file()


    def get_container(self, container_id: str) -> Optional[Container]:
        return self._containers.get(container_id)

    def get_all_containers(self) -> List[Container]:
        return list(self._containers.values())

    def update_container_state(self, container_id: str, new_state: State, **kwargs) -> bool:
        if container_id not in self._containers:
            return False

        container = self._containers[container_id]
        container.state = new_state

        for key, value in kwargs.items():
            if hasattr(container, key):
                setattr(container, key, value)

        self._save_to_file()
        return True

    def remove_container(self, container_id: str) -> None:
        if container_id in self._containers:
            del self._containers[container_id]
            self._save_to_file()
            return True
        return False


    def _save_to_file(self):
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

    def _serialize_container(self, container: Container) -> dict:
        return container.to_dict()

    def _deserialize_container(self, container_data: dict) -> Container:
        return Container.from_dict(container_data)
