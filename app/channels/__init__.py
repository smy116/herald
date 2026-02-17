"""Channel handler registry — Strategy + Registry pattern for pluggable channels."""

from abc import ABC, abstractmethod
from typing import ClassVar


class ChannelHandler(ABC):
    """Abstract base class for all channel handlers."""

    type_name: ClassVar[str] = ""
    display_name: ClassVar[str] = ""
    icon: ClassVar[str] = ""  # Remix Icon class, e.g. "ri-webhook-line"
    config_schema: ClassVar[list[dict]] = []
    """
    Describes the config fields this channel requires.
    Each item: {"key": "url", "label": "URL", "type": "text|url|email|password|textarea|select",
                "required": True, "placeholder": "...", "options": [...]}
    """

    @abstractmethod
    async def send(self, config: dict, title: str, body: str) -> None:
        """Send a message. Raise on failure."""
        ...

    def validate_config(self, config: dict) -> None:
        """Validate config against config_schema. Raises ValueError on missing required fields."""
        for field in self.config_schema:
            if field.get("required") and not config.get(field["key"], ""):
                raise ValueError(f"缺少必填配置项: {field['label']}")


# ── Global Registry ──────────────────────────────────────

_registry: dict[str, type[ChannelHandler]] = {}


def register(cls: type[ChannelHandler]) -> type[ChannelHandler]:
    """Class decorator: auto-register a handler by its type_name."""
    if not cls.type_name:
        raise ValueError(f"{cls.__name__} must define type_name")
    _registry[cls.type_name] = cls
    return cls


def get_handler(type_name: str) -> ChannelHandler:
    """Instantiate and return a handler for the given type."""
    cls = _registry.get(type_name)
    if not cls:
        raise ValueError(f"未知的渠道类型: {type_name}")
    return cls()


def all_types() -> dict[str, type[ChannelHandler]]:
    """Return a copy of the registry."""
    return dict(_registry)


# ── Auto-import all handler modules to trigger registration ──
from app.channels import webhook, telegram, email  # noqa: E402, F401
