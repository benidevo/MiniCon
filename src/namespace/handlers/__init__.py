"""Namespace handlers."""

import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


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

    def __init__(self) -> None:
        """Initialize the namespace handler with common attributes."""
        self._child_pid: Optional[int] = None

    @abstractmethod
    def setup(self) -> None:
        """Set up the namespace for a container.

        This method should be called after the container process has been
        created and before the container process has been started.

        Raises:
            NotImplementedError: If not implemented by a subclass.
        """
        raise NotImplementedError

    def fork_in_new_namespace(self, child_func: Callable[[], Any]) -> int:
        """Fork a process in the new namespace.

        This should be called after setup() by the orchestrator.
        The child process will be PID 1 in the new namespace.

        Args:
            child_func: Function to call in the child process.

        Returns:
            The PID (in the parent namespace) of the forked child.
        """
        pid = os.fork()
        if pid == 0:
            try:
                exit_code = child_func()
                os._exit(exit_code if isinstance(exit_code, int) else 0)
            except Exception as e:
                logger.error(f"Error in container process: {e}")
                os._exit(1)
        else:
            self._child_pid = pid
        return pid

    @property
    def child_pid(self) -> Optional[int]:
        """Get the PID of the child process in the parent namespace.

        Returns:
            The PID of the child or None if not created.
        """
        return self._child_pid
