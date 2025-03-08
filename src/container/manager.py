from container.registry import ContainerRegistry


class ContainerManager:
    def __init__(self):
        self.registry = ContainerRegistry()

    def create(self):
        pass

    def start(self, container_id: str):
        pass

    def stop(self , container_id: str):
        pass

    def remove(self , container_id: str):
        pass

    def list(self):
        pass

