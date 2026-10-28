from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from threading import RLock

from .models import Direction, GraphPoint, ParkingEvent, ParkingState, VehicleType


class ParkingStateManager:
    """Thread-safe occupancy state and bounded graph history."""

    def __init__(self, capacity: float = 20.0, history_size: int = 200) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = float(capacity)
        self._occupied = 0.0
        self._cars = 0
        self._bikes = 0
        self._events: deque[ParkingEvent] = deque(maxlen=history_size)
        self._graph: deque[GraphPoint] = deque(maxlen=history_size)
        self._lock = RLock()
        self._record_graph()

    def apply(self, event: ParkingEvent) -> ParkingState:
        with self._lock:
            amount = event.vehicle_type.space
            if event.direction is Direction.ENTRY:
                if self._occupied + amount > self.capacity + 1e-9:
                    raise ValueError("parking capacity exceeded")
                self._occupied += amount
                self._change_count(event.vehicle_type, 1)
            else:
                current_count = (
                    self._cars if event.vehicle_type is VehicleType.CAR else self._bikes
                )
                if current_count == 0:
                    raise ValueError("cannot exit a vehicle that is not parked")
                if self._occupied - amount < -1e-9:
                    raise ValueError("cannot exit a vehicle that is not parked")
                self._occupied = max(0.0, self._occupied - amount)
                self._change_count(event.vehicle_type, -1)
            self._events.append(event)
            self._record_graph(event.timestamp)
            return self.snapshot()

    def snapshot(self) -> ParkingState:
        with self._lock:
            return ParkingState(
                capacity=self.capacity,
                occupied=round(self._occupied, 3),
                available=round(self.capacity - self._occupied, 3),
                cars=self._cars,
                bikes=self._bikes,
                event_count=len(self._events),
                updated_at=self._graph[-1].timestamp,
            )

    def recent_events(self, limit: int = 50) -> list[ParkingEvent]:
        if limit < 1:
            raise ValueError("limit must be positive")
        with self._lock:
            return list(self._events)[-limit:][::-1]

    def graph(self, limit: int = 100) -> list[GraphPoint]:
        if limit < 1:
            raise ValueError("limit must be positive")
        with self._lock:
            return list(self._graph)[-limit:]

    def _change_count(self, vehicle_type: VehicleType, delta: int) -> None:
        if vehicle_type is VehicleType.CAR:
            self._cars += delta
        else:
            self._bikes += delta

    def _record_graph(self, timestamp: datetime | None = None) -> None:
        timestamp = timestamp or datetime.now(timezone.utc)
        self._graph.append(
            GraphPoint(
                timestamp=timestamp,
                occupied=round(self._occupied, 3),
                available=round(self.capacity - self._occupied, 3),
            )
        )
