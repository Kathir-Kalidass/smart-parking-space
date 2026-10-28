import asyncio

import pytest

from parking_app.models import Direction, ParkingEvent, VehicleType
from parking_app.simulator import ParkingSimulator


def test_deterministic_simulation_preserves_order():
    events = [
        ParkingEvent(vehicle_type=VehicleType.CAR, direction=Direction.ENTRY),
        ParkingEvent(vehicle_type=VehicleType.CAR, direction=Direction.EXIT),
    ]
    assert ParkingSimulator().deterministic(events) == events


def test_realtime_rejects_negative_interval():
    with pytest.raises(ValueError):
        asyncio.run(ParkingSimulator().realtime([], -1).__anext__())
