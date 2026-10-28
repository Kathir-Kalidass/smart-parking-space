from __future__ import annotations

from abc import ABC, abstractmethod


class GPIOAdapter(ABC):
    """Hardware boundary. Core application code depends only on this interface."""

    @abstractmethod
    def read_entry_sensor(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def read_exit_sensor(self) -> bool:
        raise NotImplementedError

    def close(self) -> None:
        pass


class SimulatedGPIO(GPIOAdapter):
    def __init__(self, entry: bool = False, exit: bool = False) -> None:
        self.entry = entry
        self.exit = exit

    def read_entry_sensor(self) -> bool:
        return self.entry

    def read_exit_sensor(self) -> bool:
        return self.exit


class RaspberryPiGPIO(GPIOAdapter):
    """Safe adapter: imports GPIO only when instantiated on a Raspberry Pi."""

    def __init__(self, entry_pin: int = 17, exit_pin: int = 27) -> None:
        try:
            import RPi.GPIO as gpio
        except ImportError as exc:
            raise RuntimeError("RPi.GPIO is required to use RaspberryPiGPIO") from exc
        self._gpio = gpio
        gpio.setmode(gpio.BCM)
        gpio.setup(entry_pin, gpio.IN, pull_up_down=gpio.PUD_DOWN)
        gpio.setup(exit_pin, gpio.IN, pull_up_down=gpio.PUD_DOWN)
        self._entry_pin = entry_pin
        self._exit_pin = exit_pin

    def read_entry_sensor(self) -> bool:
        return bool(self._gpio.input(self._entry_pin))

    def read_exit_sensor(self) -> bool:
        return bool(self._gpio.input(self._exit_pin))

    def close(self) -> None:
        self._gpio.cleanup((self._entry_pin, self._exit_pin))
