"""User namespace handler."""

from src.namespace.handlers import NamespaceHandler


class UserNamespaceHandler(NamespaceHandler):
    """Provides a specific implementation for handling User namespaces.

    This class is designed to manage the setup of a User namespace for a container.
    """

    def setup(self) -> None:
        """Sets up a User namespace for a container.

        This method should be called after the container process has been
        created and before it has been started.

        Returns:
            None
        """
        pass
