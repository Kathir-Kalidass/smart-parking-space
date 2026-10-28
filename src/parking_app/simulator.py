from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterable
from datetime import datetime, timezone
from random import Random

from .models import Direction, ParkingEvent, VehicleType


class ParkingSimulator:
    def __init__(self, seed: int = 1) -> None:
        self._random = Random(seed)

    def deterministic(self, events: Iterable[ParkingEvent]) -> list[ParkingEvent]:
        return list(events)

    def generate(self, count: int = 10) -> list[ParkingEvent]:
        if count < 0:
            raise ValueError("count must not be negative")
        return [
            ParkingEvent(
                vehicle_type=self._random.choice(list(VehicleType)),
                direction=self._random.choice(list(Direction)),
                timestamp=datetime.now(timezone.utc),
                source="simulator",
            )
            for _ in range(count)
        ]

    async def realtime(
        self, events: Iterable[ParkingEvent], interval: float = 1.0
    ) -> AsyncIterator[ParkingEvent]:
        if interval < 0:
            raise ValueError("interval must not be negative")
        for event in events:
            await asyncio.sleep(interval)
            yield event
