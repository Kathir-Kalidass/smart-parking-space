# Smart Parking Space

Smart Parking Space is an edge-oriented parking monitor. A Raspberry Pi (or the
local simulator) observes entry/exit sensors and a camera, classifies the
vehicle as a car or bike, and publishes the current occupancy to a browser or
other client in real time.

The runtime boundary is a small Python application built with **FastAPI**:

```text
sensor/camera input -> event normalization -> ML classification seam
                    -> parking-state transition -> WebSocket broadcast
```

The development implementation uses simulated sensor and camera events, so the
API and UI can be exercised without Raspberry Pi hardware. Hardware adapters and
the ML model are deliberately replaceable; they do not change the HTTP or
WebSocket contract.

## Features

- Stateful available/occupied parking-space tracking.
- Separate entry and exit event handling.
- Car/bike classification represented in every vehicle event.
- FastAPI API endpoints and a WebSocket stream for live state updates.
- Deterministic simulation for local development and demonstrations.
- A hardware boundary for Raspberry Pi GPIO and camera integration.
- An ML integration seam for a local model or a remote inference service.

## Requirements

- Python 3.10 or newer.
- A POSIX shell for the commands below (PowerShell users can use the
  equivalent activation command).
- Raspberry Pi OS and GPIO libraries only when deploying to hardware.

## Local setup

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run the development server with auto-reload:

```bash
PYTHONPATH=src python -m uvicorn parking_app.main:app --host 127.0.0.1 --port 8000 --reload
```

Use `0.0.0.0` instead of `127.0.0.1` when another device on the LAN must
connect. The interactive API documentation is at
<http://127.0.0.1:8000/docs>; the current-state endpoint is:

```bash
curl http://127.0.0.1:8000/api/state
```

The exact production-style local command is:

```bash
PYTHONPATH=src python -m uvicorn parking_app.main:app --host 0.0.0.0 --port 8000
```

If dependencies are installed in an existing virtual environment, activate it
first with `source .venv/bin/activate`. Keep `.env` and other credentials out
of source control.

## Simulation workflow

The simulator is the default development input. It emits the same normalized
events as a GPIO/camera adapter:

1. Start FastAPI with the command above.
2. Open the web client, or connect a WebSocket client to
   `ws://127.0.0.1:8000/ws/events`.
3. Select or trigger a simulated `entry` or `exit` event.
4. Select a vehicle label (`car` or `bike`) and, if supported, a slot.
5. The state manager validates the transition and broadcasts the updated
   occupancy to every connected WebSocket client.

An entry must not reduce availability below zero; an exit must not increase it
above the configured capacity. Invalid or duplicate transitions should be
reported as an event error rather than silently corrupting state. The simulator
is useful for API/UI work, WebSocket reconnect handling, and model integration
before hardware is available.

## WebSocket contract

The WebSocket endpoint is `/ws/events`. A client should expect an initial snapshot
after connecting and subsequent state/event messages. A representative state
payload is:

```json
{
  "type": "parking_state",
  "capacity": 10,
  "available": 7,
  "occupied": 3,
  "updated_at": "2026-01-01T12:00:00Z"
}
```

Input adapters should normalize events before they reach the state manager:

```json
{
  "type": "vehicle_event",
  "direction": "entry",
  "vehicle_type": "car",
  "confidence": 0.94,
  "source": "simulation"
}
```

The exact schema is owned by the application; clients should tolerate added
metadata and reconnect when the socket closes.

## ML integration seam

Classification is intentionally behind an interface (for example,
`classify(frame) -> Classification`). The simulation supplies a deterministic
`car`/`bike` result. A production adapter can call a TensorFlow Lite, ONNX, or
remote model and return:

- `vehicle_type`: `car`, `bike`, or an explicit `unknown`;
- `confidence`: a value from 0 to 1;
- optional model/version and bounding-box metadata.

Keep inference out of GPIO callbacks and out of the WebSocket handler. A
camera adapter should capture a frame, the classifier should infer it, and the
parking service should apply a validated entry/exit transition. Low-confidence
results should be visible as `unknown` or queued for review rather than
silently guessed.

## Raspberry Pi deployment

Install the application and dependencies in a virtual environment on the Pi,
then run:

```bash
source .venv/bin/activate
PYTHONPATH=src python -m uvicorn parking_app.main:app --host 0.0.0.0 --port 8000
```

For a persistent service, create a systemd unit that runs as a dedicated
non-root user, sets the project `WorkingDirectory`, loads an environment file,
and executes `/path/to/project/.venv/bin/python -m uvicorn
parking_app.main:app --host 0.0.0.0 --port 8000` with `PYTHONPATH=src` (or an
equivalent installed package path). Enable it with:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now smart-parking.service
sudo systemctl status smart-parking.service
```

Restrict port 8000 to the trusted LAN, put TLS/authentication in a reverse
proxy when exposed beyond the LAN, and configure log rotation. See
[`docs/system-design.md`](docs/system-design.md) and
[`docs/hardware-connections.md`](docs/hardware-connections.md) before wiring
hardware.

## Documentation

- [System design](docs/system-design.md) — components, data flow, simulation,
  WebSocket behavior, and deployment.
- [Hardware connections](docs/hardware-connections.md) — Raspberry Pi pin
  mapping and electrical safety.
- [Copilot instructions](.github/copilot-instructions.md) — repository-specific
  implementation guidance and commands.

## Validation

Run the repository's available checks from the activated environment:

```bash
PYTHONPATH=src python -m pytest
```

This command is intentionally explicit; if a checkout does not yet contain
tests, the command should be treated as a setup gap rather than a reason to
invent a second toolchain.
