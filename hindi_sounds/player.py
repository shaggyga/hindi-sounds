"""Event-driven, cancellable playback for the Hindi letter practice window."""
from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer


class SoundPlayer(QObject):
    """Play individual local recordings, optionally repeating the chosen group.

    ``changed`` observers can always read a valid ``current`` item. Every sound
    owns its media object and timers so signals queued by an interrupted sound
    cannot change the current selection or resume a canceled loop.
    """

    changed = Signal()
    error = Signal(str)
    LOAD_TIMEOUT_MS = 10_000

    def __init__(self, items: list[dict], audio_root: Path, parent=None):
        super().__init__(parent)
        if not items:
            raise ValueError("The letter collection is empty.")
        if any(not all(item.get(key) for key in ("id", "letter", "audio")) for item in items):
            raise ValueError("Every letter needs an id, letter, and audio filename.")
        self._all_items = list(items)
        self.items = list(items)
        self.audio_root = Path(audio_root).resolve()
        self.index = 0
        self.round = 1
        self.looping = False
        self.sounding = False
        self.phase = "ready"
        self.gap_ms = 1400
        self.volume = 0.85
        self.group = "all"
        self._generation = 0
        self._finished = False
        self._closed = False
        self._media = None
        self._output = None
        self._gap_timer = None
        self._load_timer = None

    @property
    def current(self) -> dict:
        return self.items[self.index]

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def busy(self) -> bool:
        return self.phase in ("loading", "sounding")

    def start(self):
        if self._closed:
            return
        self.looping = True
        self._play_current()

    def pause(self):
        if self._closed:
            return
        self.looping = False
        self._cancel_current()
        self.phase = "paused"
        self.changed.emit()

    def toggle(self):
        if self.looping or self.busy:
            self.pause()
        else:
            self.start()

    def replay(self):
        if not self._closed:
            self._play_current()

    def move(self, delta):
        if self._closed:
            return
        self._cancel_current()
        self._advance(int(delta))
        self._play_current()

    def select(self, index):
        if self._closed or not isinstance(index, int) or not 0 <= index < self.total:
            return
        self._cancel_current()
        self.index = index
        self._play_current()

    def set_group(self, kind):
        if self._closed:
            return
        if kind == "all":
            selected = list(self._all_items)
        elif kind == "vowels":
            selected = [item for item in self._all_items if item.get("category") in ("vowel", "sign")]
        elif kind == "consonants":
            selected = [item for item in self._all_items if item.get("category") == "consonant"]
        else:
            raise ValueError(f"Unknown letter group: {kind}")
        if not selected:
            self._cancel_current()
            self._fail(self._generation, "This group has no letters to play.")
            return
        self._cancel_current()
        self.items = selected
        self.index = 0
        self.round = 1
        self.group = kind
        if self.looping:
            self._play_current()
        else:
            self.phase = "ready"
            self.changed.emit()

    def set_volume(self, value):
        value = float(value)
        if not math.isfinite(value):
            raise ValueError("Volume must be a finite number.")
        self.volume = min(1.0, max(0.0, value))
        if self._output is not None:
            self._output.setVolume(self.volume)

    def shutdown(self):
        if self._closed:
            return
        self.looping = False
        self._cancel_current()
        self.phase = "paused"
        self._closed = True
        self.changed.emit()

    def _advance(self, delta):
        wraps, self.index = divmod(self.index + delta, self.total)
        self.round = max(1, self.round + wraps)

    def _cancel_current(self):
        # Invalidate first: stopping Qt media can emit signals synchronously.
        self._generation += 1
        self._finished = False
        for name in ("_gap_timer", "_load_timer"):
            timer = getattr(self, name)
            setattr(self, name, None)
            if timer is not None:
                timer.stop()
                timer.deleteLater()
        media, output = self._media, self._output
        self._media = self._output = None
        if media is not None:
            media.stop()
            media.deleteLater()
        if output is not None:
            output.deleteLater()
        self.sounding = False

    def _live(self, generation):
        return not self._closed and generation == self._generation and not self._finished

    def _play_current(self):
        self._cancel_current()
        generation = self._generation
        self.phase = "loading"
        self.changed.emit()
        # A changed observer may pause or navigate. Do not start the old sound.
        if not self._live(generation):
            return
        path = (self.audio_root / self.current["audio"]).resolve()
        if not path.is_file():
            self._fail(generation, f"The recording for {self.current['letter']} is missing: {path.name}.")
            return
        try:
            output = QAudioOutput(self)
            output.setVolume(self.volume)
            media = QMediaPlayer(self)
            self._output, self._media = output, media
            media.setAudioOutput(output)
            media.playbackStateChanged.connect(lambda state: self._state_changed(generation, state))
            media.mediaStatusChanged.connect(lambda status: self._status_changed(generation, status))
            media.errorOccurred.connect(lambda code, message: self._media_error(generation, code, message))
            self._arm_load_timeout(generation)
            media.setSource(QUrl.fromLocalFile(str(path)))
            if self._live(generation):
                media.play()
        except Exception as exc:
            self._fail(generation, f"The audio player could not start: {exc}")

    def _cancel_load_timeout(self):
        timer, self._load_timer = self._load_timer, None
        if timer is not None:
            timer.stop()
            timer.deleteLater()

    def _arm_load_timeout(self, generation):
        if self._load_timer is not None:
            return
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._load_timed_out(generation, timer))
        self._load_timer = timer
        timer.start(self.LOAD_TIMEOUT_MS)

    def _load_timed_out(self, generation, timer):
        if self._load_timer is timer and self.phase == "loading" and self._live(generation):
            self._fail(generation, "The recording took too long to load. Press Play to try again.")

    def _state_changed(self, generation, state):
        if not self._live(generation):
            return
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._cancel_load_timeout()
            self.sounding = True
            self.phase = "sounding"
            self.changed.emit()
        elif self._media.mediaStatus() == QMediaPlayer.MediaStatus.EndOfMedia:
            self._finish(generation)
        elif self.sounding:
            self.sounding = False
            self.phase = "loading"
            self._arm_load_timeout(generation)
            self.changed.emit()

    def _status_changed(self, generation, status):
        if not self._live(generation):
            return
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._finish(generation)
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            self._media_error(generation, QMediaPlayer.Error.FormatError, self._media.errorString())
        elif status == QMediaPlayer.MediaStatus.StalledMedia:
            self.sounding = False
            self.phase = "loading"
            self._arm_load_timeout(generation)
            self.changed.emit()
        elif status in (QMediaPlayer.MediaStatus.LoadedMedia, QMediaPlayer.MediaStatus.BufferedMedia):
            if self._media.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self._state_changed(generation, QMediaPlayer.PlaybackState.PlayingState)

    def _finish(self, generation):
        if not self._live(generation):
            return
        self._finished = True
        self._cancel_load_timeout()
        self.sounding = False
        self.phase = "gap" if self.looping else "ready"
        self.changed.emit()
        if generation != self._generation or not self.looping or self._closed:
            return
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._next_after_gap(generation))
        self._gap_timer = timer
        timer.start(max(0, int(self.gap_ms)))

    def _next_after_gap(self, generation):
        if generation != self._generation or not self.looping or self._closed:
            return
        self._advance(1)
        self._play_current()

    def _media_error(self, generation, code, message):
        if code == QMediaPlayer.Error.NoError or not self._live(generation):
            return
        detail = str(message).strip() or "The recording could not be decoded or played."
        self._fail(generation, f"Could not play {self.current['letter']}: {detail}")

    def _fail(self, generation, message):
        if generation != self._generation or self._closed or self._finished:
            return
        self.looping = False
        self._cancel_current()
        self.phase = "error"
        self.changed.emit()
        self.error.emit(str(message))
