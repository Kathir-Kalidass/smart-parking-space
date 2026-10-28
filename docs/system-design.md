# System design

## Purpose and boundaries

The system counts parking occupancy at the edge and publishes changes in real
time. FastAPI owns the process boundary and WebSocket transport; the parking
service owns state transitions; input adapters own GPIO, camera, and
simulation concerns.

```text
GPIO / camera / simulator
             |
       normalized event
             v
   classifier (ML seam)
             |
             v
      parking service ----> state repository
             |
             v
      WebSocket manager ----> browser/API clients
```

The HTTP API is for conventional inspection/control operations. The
WebSocket is for low-latency state snapshots and event notifications. Neither
transport should contain sensor timing, model inference, or occupancy rules.

## Runtime components

### FastAPI application

`parking_app.main:app` creates the ASGI application, registers API routes, and
exposes `/ws/events`. Run it locally with:

```bash
PYTHONPATH=src python -m uvicorn parking_app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Input adapters

An adapter converts a physical or simulated observation to a common event:
direction (`entry`/`exit`), vehicle type, confidence, timestamp, and source.
The simulator is deterministic and should be the default adapter in local
development. A GPIO adapter handles ultrasonic beam/distance changes; a camera
adapter captures a frame and delegates classification.

### Classification seam

The classifier is a dependency of the event pipeline, not of the HTTP layer.
Its minimum result is `vehicle_type` plus `confidence`; `unknown` is valid.
This allows a rules-based simulator, a TFLite/ONNX model on the Pi, or a
remote inference client to be selected through configuration.

### Parking state

The state service is the single writer for capacity, available, and occupied
counts. It validates boundaries and direction, applies one transition, and
emits a state snapshot plus the event outcome. Use a lock or an equivalent
serialized event queue so two simultaneous WebSocket/API actions cannot
double-count a slot.

For a multi-slot installation, replace aggregate-only state with slot IDs and
retain the same transition boundary. Persistence can start as in-memory state
for the simulator and later use SQLite or another local store if recovery
after restart is required.

### WebSocket manager

On connection, send the current snapshot. After every accepted transition,
broadcast the new snapshot and event metadata to all connected clients. Remove
dead sockets and let clients reconnect with exponential backoff. A client must
not infer occupancy by counting messages; it should use the latest snapshot.

## Simulation workflow

1. Start the API with Uvicorn.
2. Connect a browser or WebSocket client to `ws://localhost:8000/ws/events`.
3. Generate a simulated entry/exit and choose `car` or `bike` (the API helper
   is `POST /api/simulate`).
4. Normalize the event and run the classifier seam.
5. Apply a bounded state transition.
6. Broadcast the resulting snapshot and retain an error response for rejected
   transitions.

This makes UI, API, reconnect, and occupancy tests independent of GPIO timing.
Simulation events must use the same schema and service path as hardware events;
do not create a simulator-only shortcut that bypasses validation.

## ML integration

Recommended seam:

```python
classification = classifier.classify(frame)
# classification.vehicle_type, classification.confidence
event = normalizer.from_classification(observation, classification)
parking_service.apply(event)
```

Keep model files outside the repository when they are large, load the model
once at startup, and measure inference latency. Configure a confidence
threshold and record model version/source in events for troubleshooting.

## Deployment and operations

On Raspberry Pi OS, install Python and project dependencies in `.venv`, then:

```bash
source .venv/bin/activate
PYTHONPATH=src python -m uvicorn parking_app.main:app --host 0.0.0.0 --port 8000
```

Use systemd for restart-on-failure and a dedicated user. Bind to the LAN only,
firewall the port, and put authentication/TLS in a reverse proxy if remote
access is required. Monitor `/api/state`, service logs, CPU/temperature, camera
availability, and WebSocket connection count. A restart loses in-memory state;
use a local persistence adapter before relying on the service for unattended
operation.
