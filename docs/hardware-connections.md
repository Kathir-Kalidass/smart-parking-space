# Hardware connections

The following mapping is a safe starting point for a Raspberry Pi 4/5 using
BCM GPIO numbering. Confirm the physical board revision and pinout before
connecting anything.

| Function | BCM GPIO | Physical pin | Connection |
| --- | ---: | ---: | --- |
| Entry HC-SR04 TRIG | GPIO23 | 16 | Pi output to sensor TRIG |
| Entry HC-SR04 ECHO | GPIO24 | 18 | Sensor ECHO through a divider to Pi input |
| Exit HC-SR04 TRIG | GPIO25 | 22 | Pi output to sensor TRIG |
| Exit HC-SR04 ECHO | GPIO12 | 32 | Sensor ECHO through a divider to Pi input |
| Status/entry LED (optional) | GPIO17 | 11 | LED through a resistor |
| Status/exit LED (optional) | GPIO27 | 13 | LED through a resistor |
| Ground | — | 6/9/14/20/25/30/34/39 | Common ground |
| Camera | CSI connector | — | Raspberry Pi camera ribbon connector |

Power the HC-SR04 from a suitable 5 V rail (physical pin 2 or 4) and connect
its ground to a Pi ground. Do not use GPIO numbers as physical pin numbers in
software or wiring documentation: the application should explicitly select
BCM numbering.

## Critical HC-SR04 safety note

The HC-SR04 ECHO output is typically **5 V**. Raspberry Pi GPIO inputs are
3.3 V only and are not 5 V tolerant. Never connect ECHO directly to a GPIO.
Use a two-resistor voltage divider for each ECHO line, for example:

```text
HC-SR04 ECHO --- 1 kΩ ---+--- Pi GPIO input
                         |
                        2 kΩ
                         |
                        GND
```

This scales 5 V to approximately 3.3 V. Use appropriate resistor values,
verify the resulting voltage with a multimeter, and power down before changing
wiring. A level-shifter module is an acceptable alternative. TRIG is a Pi
3.3 V output and is normally recognized by the sensor.

## Sensor placement and behavior

Mount each ultrasonic sensor so its detection cone crosses the intended lane,
not a nearby wall or the ground. Measure a baseline distance, choose a
presence threshold with hysteresis, and debounce readings so one vehicle does
not generate repeated entries. Two sensors or a camera can determine direction;
an individual distance reading alone cannot reliably distinguish entry from
exit.

The GPIO adapter should:

1. Configure TRIG as output and ECHO as input.
2. Trigger a short pulse and measure the ECHO duration with a timeout.
3. Convert duration to distance.
4. Apply filtering/debounce and emit a normalized event.
5. Leave classification and occupancy updates to the shared application path.

Never block the FastAPI event loop with a busy GPIO measurement loop. Use a
background worker/task and publish completed observations into the application
event queue.

## Camera and power

Use the CSI connector and enable the camera through Raspberry Pi OS settings.
Provide a stable power supply sized for the Pi, camera, sensors, and any LEDs.
Keep sensor and camera cables away from noisy motor/power wiring. A prototype
should be tested with the Pi powered off while wiring and with current limits
considered for every accessory.

## Simulation before hardware

Run the simulator first and verify entry/exit bounds, WebSocket broadcasts, and
reconnect behavior. Then test one sensor at a time with the camera disabled.
Compare measured distances with expected values, inspect logs, and only then
enable the complete sensor-to-classifier pipeline.
