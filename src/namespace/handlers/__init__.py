"""Namespace handlers."""

from abc import ABC, abstractmethod


class NamespaceHandler(ABC):
    """Abstract base class for namespace handlers.

    This class provides a common interface for different namespace handlers.
    Concrete subclasses must implement the `setup` method to provide specific
    namespace setup logic.

    Attributes:
        None

    Methods:
        setup: Abstract method to set up the namespace for a container.
    """

    @abstractmethod
    def setup(self) -> None:
        """Set up the namespace for a container.

        This method should be called after the container process has been
        created and before the container process has been started.

        Raises:
            NotImplementedError: If not implemented by a subclass.
        """
        raise NotImplementedError
