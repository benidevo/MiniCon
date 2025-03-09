"""Mount namespace handler."""

from src.namespace.handlers import NamespaceHandler


class MountNamespaceHandler(NamespaceHandler):
    """Provides a specific implementation for handling Mount namespaces.

    This class is designed to manage the setup of a Mount namespace for a container.
    """

    def setup(self) -> None:
        """Sets up a Mount namespace for a container.

        This method should be called after the container process has been
        created and before it has been started.

        Returns:
            None
        """
        pass
