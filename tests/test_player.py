"""Focused playback-state tests; no audio hardware or wall-clock waits required."""
from pathlib import Path
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication
from PySide6.QtMultimedia import QMediaPlayer as QtMediaPlayer

from hindi_sounds import player as module


class FakeSignal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self, *args):
        for callback in list(self.callbacks):
            callback(*args)


class FakeTimer:
    instances = []

    def __init__(self, parent=None):
        self.timeout = FakeSignal()
        self.active = False
        self.deleted = False
        self.interval = None
        self.instances.append(self)

    def setSingleShot(self, enabled):
        self.single_shot = enabled

    def start(self, interval):
        self.interval = interval
        self.active = True

    def stop(self):
        self.active = False

    def isActive(self):
        return self.active

    def deleteLater(self):
        self.deleted = True

    def fire(self, even_canceled=False):
        active = self.active
        self.active = False
        if active or even_canceled:
            self.timeout.emit()


class FakeOutput:
    def __init__(self, parent=None):
        self.volume = None
        self.deleted = False

    def setVolume(self, volume):
        self.volume = volume

    def deleteLater(self):
        self.deleted = True


class FakeMedia:
    PlaybackState = QtMediaPlayer.PlaybackState
    MediaStatus = QtMediaPlayer.MediaStatus
    Error = QtMediaPlayer.Error
    instances = []
    play_exception = False
    source_error = False

    def __init__(self, parent=None):
        self.playbackStateChanged = FakeSignal()
        self.mediaStatusChanged = FakeSignal()
        self.errorOccurred = FakeSignal()
        self.state = self.PlaybackState.StoppedState
        self.status = self.MediaStatus.NoMedia
        self.message = ""
        self.stop_calls = 0
        self.play_calls = 0
        self.deleted = False
        self.instances.append(self)

    def setAudioOutput(self, output):
        self.output = output

    def setSource(self, url):
        self.source = url.toLocalFile()
        if self.source_error:
            self.fail("File format not supported")

    def play(self):
        self.play_calls += 1
        if self.play_exception:
            raise RuntimeError("Audio backend unavailable")

    def stop(self):
        self.stop_calls += 1
        self.set_state(self.PlaybackState.StoppedState)

    def deleteLater(self):
        self.deleted = True

    def playbackState(self):
        return self.state

    def mediaStatus(self):
        return self.status

    def errorString(self):
        return self.message

    def set_state(self, state):
        self.state = state
        self.playbackStateChanged.emit(state)

    def set_status(self, status):
        self.status = status
        self.mediaStatusChanged.emit(status)

    def playing(self):
        self.set_state(self.PlaybackState.PlayingState)

    def ended(self):
        self.set_status(self.MediaStatus.EndOfMedia)
        self.set_state(self.PlaybackState.StoppedState)

    def fail(self, message="Device unavailable"):
        self.message = message
        self.errorOccurred.emit(self.Error.ResourceError, message)


class SoundPlayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "audio").mkdir()
        self.items = [
            {"id": "a", "letter": "अ", "roman": "a", "category": "vowel", "audio": "audio/a.wav"},
            {"id": "am", "letter": "अं", "roman": "am", "category": "sign", "audio": "audio/am.wav"},
            {"id": "ka", "letter": "क", "roman": "ka", "category": "consonant", "audio": "audio/ka.wav"},
            {"id": "kha", "letter": "ख", "roman": "kha", "category": "consonant", "audio": "audio/kha.wav"},
        ]
        for item in self.items:
            (self.root / item["audio"]).write_bytes(b"fake audio; media is injected")
        FakeMedia.instances = []
        FakeMedia.play_exception = False
        FakeMedia.source_error = False
        FakeTimer.instances = []
        for name, replacement in (("QMediaPlayer", FakeMedia), ("QAudioOutput", FakeOutput), ("QTimer", FakeTimer)):
            patcher = patch.object(module, name, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.player = module.SoundPlayer(self.items, self.root)
        self.addCleanup(self.player.shutdown)
        self.states = []
        self.errors = []
        self.player.changed.connect(self.capture)
        self.player.error.connect(self.errors.append)

    def capture(self):
        self.states.append((self.player.current["id"], self.player.phase, self.player.sounding, self.player.looping))

    @property
    def media(self):
        return FakeMedia.instances[-1]

    def test_initial_state_and_actual_playing_state_control_flash(self):
        self.assertEqual(self.player.current["id"], "a")
        self.assertEqual(self.player.total, 4)
        self.assertEqual(self.player.phase, "ready")
        self.player.start()
        self.assertEqual(self.player.phase, "loading")
        self.assertFalse(self.player.sounding)
        self.assertTrue(self.player.looping)
        self.assertEqual(Path(self.media.source), self.root / "audio/a.wav")
        self.media.set_status(FakeMedia.MediaStatus.LoadedMedia)
        self.assertFalse(self.player.sounding)
        self.media.playing()
        self.assertTrue(self.player.sounding)
        self.assertEqual(self.player.phase, "sounding")
        self.assertIsNone(self.player._load_timer)

    def test_end_event_then_gap_advance_and_continuous_wrap(self):
        self.player.start()
        for step in range(9):
            self.assertEqual(self.player.index, step % 4)
            self.assertEqual(self.player.round, step // 4 + 1)
            self.media.playing()
            self.assertIsNone(self.player._gap_timer)
            self.player.gap_ms = 700
            self.media.ended()
            self.assertEqual(self.player.phase, "gap")
            self.assertFalse(self.player.sounding)
            self.assertEqual(self.player.index, step % 4)
            self.assertEqual(self.player._gap_timer.interval, 700)
            self.player._gap_timer.fire()
        self.assertEqual(self.player.index, 1)
        self.assertEqual(self.player.round, 3)
        self.assertEqual(len(FakeMedia.instances), 10)

    def test_pause_invalidates_queued_media_events_and_timeouts(self):
        self.player.start()
        old_media, old_timer = self.media, self.player._load_timer
        self.player.pause()
        state_count = len(self.states)
        old_media.playing()
        old_media.ended()
        old_media.fail()
        old_timer.fire(even_canceled=True)
        self.assertEqual(len(self.states), state_count)
        self.assertEqual(self.player.phase, "paused")
        self.assertFalse(self.player.sounding)
        self.assertFalse(self.player.looping)
        self.assertEqual(self.player.index, 0)
        self.assertEqual(old_media.stop_calls, 1)
        self.assertTrue(old_media.deleted)
        self.assertFalse(self.errors)

    def test_pause_during_gap_blocks_already_queued_timeout(self):
        self.player.start()
        self.media.ended()
        old_timer = self.player._gap_timer
        self.player.pause()
        old_timer.fire(even_canceled=True)
        self.assertEqual(self.player.index, 0)
        self.assertEqual(len(FakeMedia.instances), 1)
        self.assertEqual(self.player.phase, "paused")

    def test_looping_replay_discards_old_gap_and_keeps_position(self):
        self.player.start()
        old_media = self.media
        self.media.ended()
        old_timer = self.player._gap_timer
        self.player.replay()
        old_timer.fire(even_canceled=True)
        old_media.ended()
        old_media.fail()
        self.assertEqual(self.player.current["id"], "a")
        self.assertEqual(len(FakeMedia.instances), 2)
        self.assertTrue(self.player.looping)
        self.media.ended()
        self.player._gap_timer.fire()
        self.assertEqual(self.player.current["id"], "am")

    def test_paused_replay_move_and_select_are_one_shots(self):
        self.player.pause()
        for operation, expected in ((self.player.replay, "a"), (lambda: self.player.move(1), "am"), (lambda: self.player.select(3), "kha")):
            operation()
            self.assertEqual(self.player.current["id"], expected)
            self.assertFalse(self.player.looping)
            self.media.playing()
            self.media.ended()
            self.assertEqual(self.player.phase, "ready")
            self.assertIsNone(self.player._gap_timer)
        self.player.select(99)
        self.assertEqual(self.player.current["id"], "kha")

    def test_rapid_navigation_ignores_every_older_generation(self):
        self.player.start()
        self.player.move(1)
        self.player.move(1)
        self.player.move(-1)
        self.player.select(3)
        current = self.media
        state_count = len(self.states)
        for old in FakeMedia.instances[:-1]:
            old.playing()
            old.ended()
            old.fail()
        for timer in list(FakeTimer.instances[:-1]):
            timer.fire(even_canceled=True)
        self.assertEqual(len(self.states), state_count)
        self.assertEqual(self.player.current["id"], "kha")
        current.playing()
        self.assertTrue(self.player.sounding)
        current.ended()
        self.player._gap_timer.fire()
        self.assertEqual(self.player.current["id"], "a")
        self.assertEqual(self.player.round, 2)

    def test_filters_include_signs_reset_round_and_preserve_loop_mode(self):
        self.player.set_group("vowels")
        self.assertEqual([item["id"] for item in self.player.items], ["a", "am"])
        self.assertFalse(FakeMedia.instances)
        self.player.start()
        old = self.media
        self.player.round = 4
        self.player.set_group("consonants")
        self.assertEqual(self.player.current["id"], "ka")
        self.assertEqual(self.player.round, 1)
        self.assertEqual(self.player.total, 2)
        self.assertTrue(self.player.looping)
        old.ended()
        self.assertIsNone(self.player._gap_timer)
        self.player.pause()
        self.player.set_group("all")
        self.assertEqual(self.player.total, 4)
        self.assertEqual(self.player.phase, "ready")
        self.assertFalse(self.player.looping)

    def test_missing_audio_is_descriptive_and_retry_works(self):
        path = self.root / self.items[0]["audio"]
        path.unlink()
        self.player.start()
        self.assertEqual(self.player.phase, "error")
        self.assertFalse(self.player.looping)
        self.assertIn("a.wav", self.errors[-1])
        self.assertIn("missing", self.errors[-1])
        self.assertFalse(FakeMedia.instances)
        path.write_bytes(b"restored")
        self.player.start()
        self.assertEqual(self.player.phase, "loading")
        self.assertEqual(self.player.current["id"], "a")

    def test_media_error_halts_and_invalid_media_uses_description(self):
        self.player.start()
        old = self.media
        old.fail("Device unavailable")
        self.assertEqual(self.player.phase, "error")
        self.assertFalse(self.player.looping)
        self.assertIn("Device unavailable", self.errors[-1])
        old.ended()
        self.assertIsNone(self.player._gap_timer)
        self.player.start()
        self.media.message = "Unsupported recording"
        self.media.set_status(FakeMedia.MediaStatus.InvalidMedia)
        self.assertEqual(self.player.phase, "error")
        self.assertIn("Unsupported recording", self.errors[-1])

    def test_synchronous_backend_failures_do_not_start_canceled_media(self):
        FakeMedia.source_error = True
        self.player.start()
        self.assertEqual(self.player.phase, "error")
        self.assertEqual(self.media.play_calls, 0)
        FakeMedia.source_error = False
        FakeMedia.play_exception = True
        self.player.start()
        self.assertEqual(self.player.phase, "error")
        self.assertIn("Audio backend unavailable", self.errors[-1])
        self.assertIsNone(self.player._media)

    def test_load_and_stall_timeouts_are_cancellable_and_generation_safe(self):
        self.player.start()
        initial_timeout = self.player._load_timer
        self.media.playing()
        initial_timeout.fire(even_canceled=True)
        self.assertEqual(self.player.phase, "sounding")
        self.media.set_status(FakeMedia.MediaStatus.StalledMedia)
        stall_timeout = self.player._load_timer
        self.assertIsNot(stall_timeout, initial_timeout)
        initial_timeout.fire(even_canceled=True)
        self.assertEqual(self.player.phase, "loading")
        self.assertFalse(self.errors)
        stall_timeout.fire()
        self.assertEqual(self.player.phase, "error")
        self.assertFalse(self.player.looping)
        self.assertIn("too long", self.errors[-1])
        self.player.start()
        self.player._load_timer.fire()
        self.assertEqual(self.player.phase, "error")

    def test_duplicate_end_and_late_playing_do_not_create_extra_timers(self):
        self.player.start()
        media = self.media
        media.ended()
        timer = self.player._gap_timer
        count = len(FakeTimer.instances)
        media.ended()
        media.playing()
        media.fail()
        self.assertEqual(self.player.phase, "gap")
        self.assertFalse(self.player.sounding)
        self.assertEqual(len(FakeTimer.instances), count)
        timer.fire()
        timer.fire(even_canceled=True)
        self.assertEqual(self.player.index, 1)
        self.assertEqual(len(FakeMedia.instances), 2)

    def test_volume_is_clamped_and_applied_to_current_and_future_output(self):
        self.player.set_volume(0.3)
        self.player.start()
        self.assertAlmostEqual(self.media.output.volume, 0.3)
        self.player.set_volume(2.0)
        self.assertEqual(self.media.output.volume, 1.0)
        self.player.replay()
        self.assertEqual(self.media.output.volume, 1.0)
        self.player.set_volume(-1)
        self.assertEqual(self.player.volume, 0.0)
        with self.assertRaises(ValueError):
            self.player.set_volume(float("nan"))

    def test_backward_wrap_and_large_moves_keep_a_valid_index(self):
        self.player.move(-1)
        self.assertEqual(self.player.index, 3)
        self.assertEqual(self.player.round, 1)
        self.player.move(9)
        self.assertEqual(self.player.index, 0)
        self.assertEqual(self.player.round, 4)
        self.player.move(-100)
        self.assertTrue(0 <= self.player.index < self.player.total)
        self.assertEqual(self.player.round, 1)

    def test_shutdown_is_idempotent_and_blocks_all_future_playback(self):
        self.player.start()
        media, timer = self.media, self.player._load_timer
        self.player.shutdown()
        state_count = len(self.states)
        self.player.shutdown()
        for operation in (self.player.start, self.player.toggle, self.player.replay, lambda: self.player.move(1), lambda: self.player.select(2), lambda: self.player.set_group("vowels")):
            operation()
        media.playing()
        media.ended()
        media.fail()
        timer.fire(even_canceled=True)
        self.assertEqual(len(self.states), state_count)
        self.assertEqual(len(FakeMedia.instances), 1)
        self.assertEqual(self.player.phase, "paused")
        self.assertFalse(self.player.looping)

    def test_empty_collections_rejected_and_empty_filters_keep_valid_current(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            module.SoundPlayer([], self.root)
        player = module.SoundPlayer(self.items[:2], self.root)
        self.addCleanup(player.shutdown)
        errors = []
        player.error.connect(errors.append)
        player.set_group("consonants")
        self.assertEqual(player.current["id"], "a")
        self.assertEqual(player.phase, "error")
        self.assertIn("no letters", errors[-1])

    def test_observer_pause_during_loading_prevents_audio_creation(self):
        def pause_when_loading():
            if self.player.phase == "loading":
                self.player.pause()
        self.player.changed.connect(pause_when_loading)
        self.player.start()
        self.assertEqual(self.player.phase, "paused")
        self.assertFalse(FakeMedia.instances)

    def test_observer_pause_at_end_prevents_scheduling_a_gap(self):
        def pause_at_gap():
            if self.player.phase == "gap":
                self.player.pause()
        self.player.changed.connect(pause_at_gap)
        self.player.start()
        self.media.ended()
        self.assertEqual(self.player.phase, "paused")
        self.assertIsNone(self.player._gap_timer)


if __name__ == "__main__":
    unittest.main()
