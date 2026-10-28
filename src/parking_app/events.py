from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from typing import Any

Subscriber = Callable[[Any], Any | Awaitable[Any]]


class EventBus:
    """Small in-process pub/sub bus; subscribers are called in registration order."""

    def __init__(self) -> None:
        self._subscribers: list[Subscriber] = []
        self._lock = asyncio.Lock()

    async def subscribe(self, callback: Subscriber) -> None:
        async with self._lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)

    async def unsubscribe(self, callback: Subscriber) -> None:
        async with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    async def publish(self, event: Any) -> None:
        async with self._lock:
            subscribers = list(self._subscribers)
        for callback in subscribers:
            result = callback(event)
            if inspect.isawaitable(result):
                await result

