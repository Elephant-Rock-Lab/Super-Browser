"""Plugin slots — deferred interface for extensible capability registration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from super_browser.agent.types import PluginSlotKey


class PluginSlot(ABC):

    @abstractmethod
    def slot_key(self) -> PluginSlotKey: ...

    @abstractmethod
    async def initialize(self, context: dict) -> None: ...

    @abstractmethod
    async def shutdown(self) -> None: ...


class PluginRegistry:

    def __init__(self) -> None:
        self._slots: dict[PluginSlotKey, PluginSlot] = {}

    def register(self, plugin: PluginSlot) -> None:
        key = plugin.slot_key()
        if key in self._slots:
            raise ValueError(f"Plugin slot '{key.value}' is already occupied by {type(self._slots[key]).__name__}")
        self._slots[key] = plugin

    def get(self, key: PluginSlotKey) -> Optional[PluginSlot]:
        return self._slots.get(key)

    def unregister(self, key: PluginSlotKey) -> None:
        self._slots.pop(key, None)
