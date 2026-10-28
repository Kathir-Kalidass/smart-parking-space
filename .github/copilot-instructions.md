# Copilot instructions for smart-parking-space

## Repository context

This is a Python edge/IoT parking application. The runtime is a FastAPI ASGI
service with a WebSocket endpoint and a deterministic simulator for local
development. Raspberry Pi GPIO and camera adapters feed the same normalized
event path as simulation; they must not duplicate occupancy logic.

The core data flow is:

```text
sensor/camera/simulator -> normalized event -> ML classifier seam
-> bounded parking-state transition -> WebSocket broadcast
```

Read [README.md](../README.md), [docs/system-design.md](../docs/system-design.md),
and [docs/hardware-connections.md](../docs/hardware-connections.md) before
changing architecture or hardware-facing behavior.

## Exact development commands

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
PYTHONPATH=src python -m uvicorn parking_app.main:app --host 127.0.0.1 --port 8000 --reload
```

Health/API checks:

```bash
curl http://127.0.0.1:8000/api/state
# interactive OpenAPI documentation:
# http://127.0.0.1:8000/docs
```

Production-style local or Pi run:

```bash
PYTHONPATH=src python -m uvicorn parking_app.main:app --host 0.0.0.0 --port 8000
```

Validation commands:

```bash
PYTHONPATH=src python -m pytest
```

Do not introduce a second package manager or command convention without
updating this file and the README.

## Architecture rules

- Keep FastAPI routes and WebSocket handlers thin.
- Keep GPIO timing, camera capture, and simulation generation in adapters.
- Keep classification behind an injectable seam returning `vehicle_type` and
  `confidence`; `unknown` is preferable to an unjustified guess.
- Make one parking-state service the single writer for capacity, availability,
  and slot transitions.
- Validate entry/exit bounds and make event handling idempotent where event IDs
  are available.
- Broadcast snapshots after accepted transitions; clients consume the latest
  snapshot rather than counting messages.
- Keep sensor work off the ASGI event loop and handle WebSocket disconnects.
- Preserve the simulation path so API/UI and model work can be tested without a
  Raspberry Pi.

## Hardware safety

Use BCM numbering. The documented mapping uses GPIO23/24 for entry and
GPIO25/12 for exit. HC-SR04 ECHO is normally 5 V: it **must** pass through a
voltage divider or level shifter before reaching a 3.3 V Pi GPIO. Never wire
ECHO directly. See the hardware document for the complete pin table and
physical-pin numbers.

## Deployment expectations

Run on Raspberry Pi OS in a dedicated virtual environment and preferably under
systemd as a non-root user. Bind to `0.0.0.0` only when LAN access is needed,
restrict the port with a firewall, and use a reverse proxy for TLS/authentication
outside a trusted LAN. In-memory state is suitable for simulation; add a
persistence adapter before unattended production deployment.

Do not edit source, UI, tests, or dependency manifests for documentation-only
requests. Keep model files and credentials out of Git.
