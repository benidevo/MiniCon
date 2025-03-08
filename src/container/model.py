from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
import json
from typing import List, Optional


class State(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    EXITED = "exited"


@dataclass
class Container:
    name: str
    id: str
    process_id: Optional[int]
    command: List[str]
    state: State = State.CREATED
    exit_code: Optional[int] = None
    root_fs: str
    hostname: str
    memory_limit: int
    created_at: datetime = datetime.now()
    started_at: Optional[datetime] = None
    exited_at: Optional[datetime] = None

    def to_dict(self):
        data = asdict(self)
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat() if value else None
            elif isinstance(value, Enum):
                data[key] = value.value
        return data
    @classmethod
    def from_dict(cls, data: dict) -> "Container":
        if "state" in data and isinstance(data["state"], str):
            data["state"] = State(data["state"])

        for date_field in ["created_at", "started_at", "exited_at"]:
            if date_field in data and data[date_field]:
                if isinstance(data[date_field], str):
                    data[date_field] = datetime.fromisoformat(data[date_field])

        return cls(**data)

    def to_json(self):
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "Container":
        return cls.from_dict(json.loads(json_str))
