"""Container model and state management."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional


class State(str, Enum):
    """Container state enum.

    Represents the possible states of a container during its lifecycle.
    """

    CREATED = "created"
    RUNNING = "running"
    EXITED = "exited"


@dataclass
class Container:
    """Container model representing a running or stopped container.

    This class manages the container metadata, including its state transitions
    and serialization/deserialization to persistent storage.

    Attributes:
        name: Human-readable name for the container
        id: Unique identifier for the container
        process_id: PID of the container process on the host
        command: Command and arguments to run in the container
        state: Current state of the container (created, running, exited)
        exit_code: Exit code of the container process (if exited)
        root_fs: Path to the container's root filesystem
        hostname: Container's hostname
        memory_limit: Memory limit in bytes
        created_at: Timestamp when the container was created
        started_at: Timestamp when the container was started
        exited_at: Timestamp when the container exited
    """

    name: str
    id: str
    command: List[str]
    root_fs: str
    hostname: str
    memory_limit: int
    process_id: Optional[int] = None
    state: State = State.CREATED
    exit_code: int = 0
    created_at: datetime = datetime.now()
    started_at: Optional[datetime] = None
    exited_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Serialize the container to a dictionary.

        The serialized dictionary is a simple representation of the container's
        metadata, with datetime fields converted to ISO 8601 strings and enum
        fields converted to their string values.

        Returns:
            A dictionary containing the container's metadata.
        """
        data = asdict(self)
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat() if value else None
            elif isinstance(value, Enum):
                data[key] = value.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Container":
        """Create a Container instance from a dictionary.

        This method deserializes a dictionary representation of a container's
        metadata into a Container object. It handles the conversion of string
        representations of enum and datetime fields to their respective types.

        Args:
            data: A dictionary containing the container's metadata.

        Returns:
            A Container instance populated with the data from the dictionary.
        """
        if "state" in data and isinstance(data["state"], str):
            data["state"] = State(data["state"])

        for date_field in ["created_at", "started_at", "exited_at"]:
            if date_field in data and data[date_field]:
                if isinstance(data[date_field], str):
                    data[date_field] = datetime.fromisoformat(data[date_field])

        return cls(**data)

    def to_json(self) -> str:
        """Serialize the container to a JSON string.

        This method is a wrapper around the `to_dict` method, serializing the
        container's metadata to a JSON string.

        Returns:
            A JSON string containing the container's metadata.
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "Container":
        """Create a Container instance from a JSON string.

        This method deserializes a JSON string representation of a container's
        metadata into a Container object. It is a wrapper around the `from_dict`
        method, handling the conversion of the JSON string to a dictionary.

        Args:
            json_str: A JSON string containing the container's metadata.

        Returns:
            A Container instance populated with the data from the JSON string.
        """
        return cls.from_dict(json.loads(json_str))
