from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from PySide6.QtCore import QObject, QTimer, Signal


@dataclass
class NavigationRepeater:
    initial_delay: float = 0.36
    repeat_delay: float = 0.095
    _pressed_at: dict[str, float] = field(default_factory=dict)
    _repeated_at: dict[str, float] = field(default_factory=dict)

    def update(self, action: str, pressed: bool, now: float) -> bool:
        if not pressed:
            self._pressed_at.pop(action, None)
            self._repeated_at.pop(action, None)
            return False
        if action not in self._pressed_at:
            self._pressed_at[action] = now
            self._repeated_at[action] = now
            return True
        if now - self._pressed_at[action] < self.initial_delay:
            return False
        if now - self._repeated_at[action] >= self.repeat_delay:
            self._repeated_at[action] = now
            return True
        return False


class ControllerManager(QObject):
    action = Signal(str)
    connection_changed = Signal(str)

    BUTTON_ACTIONS = {
        "CONTROLLER_BUTTON_A": "accept",
        "CONTROLLER_BUTTON_B": "back",
        "CONTROLLER_BUTTON_X": "extra",
        "CONTROLLER_BUTTON_Y": "english",
        "CONTROLLER_BUTTON_BACK": "help",
        "CONTROLLER_BUTTON_START": "menu",
        "CONTROLLER_BUTTON_LEFTSHOULDER": "page_left",
        "CONTROLLER_BUTTON_RIGHTSHOULDER": "page_right",
        "CONTROLLER_BUTTON_DPAD_UP": "up",
        "CONTROLLER_BUTTON_DPAD_DOWN": "down",
        "CONTROLLER_BUTTON_DPAD_LEFT": "left",
        "CONTROLLER_BUTTON_DPAD_RIGHT": "right",
    }

    def __init__(self, parent: QObject | None = None, dead_zone: float = 0.58):
        super().__init__(parent)
        self.dead_zone = dead_zone
        self._pygame = None
        self._controller_api = None
        self._controller = None
        self._buttons: dict[str, bool] = {}
        self._repeater = NavigationRepeater()
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self.poll)
        self._initialize()

    def _initialize(self) -> None:
        try:
            import pygame
            from pygame._sdl2 import controller

            pygame.init()
            controller.init()
            self._pygame = pygame
            self._controller_api = controller
            self._open_first()
            self._timer.start()
        except Exception as exc:
            self.connection_changed.emit(f"Controller input unavailable: {exc}")

    def _open_first(self) -> None:
        if not self._controller_api or self._controller is not None:
            return
        try:
            if self._controller_api.get_count() > 0:
                self._controller = self._controller_api.Controller(0)
                self.connection_changed.emit(f"Controller connected: {self._controller.name}")
        except Exception:
            self._controller = None

    @property
    def connected(self) -> bool:
        try:
            return bool(self._controller and self._controller.attached())
        except Exception:
            return False

    def poll(self) -> None:
        if not self._pygame:
            return
        try:
            self._pygame.event.pump()
            if self._controller and not self._controller.attached():
                self._controller = None
                self._buttons.clear()
                self.connection_changed.emit("Controller disconnected")
            self._open_first()
            if not self._controller:
                return
            now = time.monotonic()
            states: dict[str, bool] = {}
            for constant_name, action in self.BUTTON_ACTIONS.items():
                constant = getattr(self._pygame, constant_name)
                states[action] = bool(self._controller.get_button(constant))
            x = self._controller.get_axis(self._pygame.CONTROLLER_AXIS_LEFTX) / 32768.0
            y = self._controller.get_axis(self._pygame.CONTROLLER_AXIS_LEFTY) / 32768.0
            if abs(x) > abs(y):
                states["left"] = states["left"] or x < -self.dead_zone
                states["right"] = states["right"] or x > self.dead_zone
            else:
                states["up"] = states["up"] or y < -self.dead_zone
                states["down"] = states["down"] or y > self.dead_zone
            repeatable = {"up", "down", "left", "right"}
            for action, pressed in states.items():
                previous = self._buttons.get(action, False)
                fire = self._repeater.update(action, pressed, now) if action in repeatable else pressed and not previous
                if fire:
                    self.action.emit(action)
            self._buttons = states
        except Exception as exc:
            self._controller = None
            self.connection_changed.emit(f"Controller input recovered from error: {exc}")

    def shutdown(self) -> None:
        self._timer.stop()
        try:
            if self._controller:
                self._controller.quit()
            if self._controller_api:
                self._controller_api.quit()
            if self._pygame:
                self._pygame.quit()
        except Exception:
            pass
