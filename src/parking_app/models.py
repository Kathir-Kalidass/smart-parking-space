from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class VehicleType(str, Enum):
    CAR = "car"
    BIKE = "bike"

    @property
    def space(self) -> float:
        return 1.0 if self is VehicleType.CAR else 0.5


class Direction(str, Enum):
    ENTRY = "entry"
    EXIT = "exit"


class ParkingEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    vehicle_type: VehicleType
    direction: Direction
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "simulator"


class ParkingState(BaseModel):
    capacity: float
    occupied: float
    available: float
    cars: int
    bikes: int
    event_count: int = 0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GraphPoint(BaseModel):
    timestamp: datetime
    occupied: float
    available: float


class EventRequest(BaseModel):
    vehicle_type: VehicleType
    direction: Direction
    source: str = "api"
    timestamp: Optional[datetime] = None
