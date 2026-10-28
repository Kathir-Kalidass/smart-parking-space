import pytest

from parking_app.models import Direction, ParkingEvent, VehicleType
from parking_app.state import ParkingStateManager


def event(vehicle_type, direction):
    return ParkingEvent(vehicle_type=vehicle_type, direction=direction)


def test_car_and_bike_entries_update_weighted_state():
    manager = ParkingStateManager()
    state = manager.apply(event(VehicleType.CAR, Direction.ENTRY))
    assert state.occupied == 1
    state = manager.apply(event(VehicleType.BIKE, Direction.ENTRY))
    assert state.occupied == 1.5
    assert state.available == 18.5
    assert (state.cars, state.bikes) == (1, 1)


def test_exit_cannot_make_occupancy_negative():
    manager = ParkingStateManager()
    with pytest.raises(ValueError, match="not parked"):
        manager.apply(event(VehicleType.BIKE, Direction.EXIT))

    manager.apply(event(VehicleType.CAR, Direction.ENTRY))
    with pytest.raises(ValueError, match="not parked"):
        manager.apply(event(VehicleType.BIKE, Direction.EXIT))


def test_capacity_is_enforced():
    manager = ParkingStateManager(capacity=1.0)
    manager.apply(event(VehicleType.CAR, Direction.ENTRY))
    with pytest.raises(ValueError, match="capacity"):
        manager.apply(event(VehicleType.BIKE, Direction.ENTRY))


def test_history_and_graph_are_bounded_and_newest_events_are_first():
    manager = ParkingStateManager(history_size=2)
    for _ in range(3):
        manager.apply(event(VehicleType.BIKE, Direction.ENTRY))
    assert len(manager.recent_events()) == 2
    assert manager.recent_events()[0].direction is Direction.ENTRY
    assert len(manager.graph()) == 2
