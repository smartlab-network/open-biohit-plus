import uuid

# Global registry for all serializable classes
CLASS_REGISTRY: dict[str, type] = {}

def register_class(cls):
    """Decorator to register classes automatically."""
    CLASS_REGISTRY[cls.__name__] = cls
    return cls

@register_class
class Serializable:
    """Base mixin for JSON serialization with registry support."""

    def to_dict(self) -> dict:
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: dict):
        """Factory: dispatch to correct subclass based on `class` field."""
        class_name = data.get("class", cls.__name__)
        target_cls = CLASS_REGISTRY.get(class_name)
        if not target_cls:
            raise ValueError(f"Unknown class '{class_name}' in registry")
        return target_cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict):
        """Default reconstruction (overridden in subclasses)."""
        raise NotImplementedError