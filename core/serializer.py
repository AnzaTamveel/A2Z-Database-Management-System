import json
from typing import Any, Dict, List
from datetime import datetime

class Serializer:
    @staticmethod
    def serialize(data: Any) -> str:
        """Serialize data to JSON string"""
        return json.dumps(data, default=Serializer._default_serializer)

    @staticmethod
    def deserialize(data: str) -> Any:
        """Deserialize JSON string to Python object"""
        return json.loads(data)

    @staticmethod
    def _default_serializer(obj: Any) -> Any:
        """Handle serialization of non-JSON-serializable objects"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")