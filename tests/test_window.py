"""Offscreen UI checks with a recording player; no audio or saved user state."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import unittest
from unittest.mock import patch

from PySide6.QtCore import QObject, QPoint, QEvent, Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from hindi_sounds import window as window_module
from hindi_sounds.settings import DEFAULTS


class RecordingPlayer(QObject):
    changed = Signal()
    error = Signal(str)

    def __init__(self, items, audio_root, parent=None):
        super().__init__(parent)
        self.all_items = items
        self.items = items
        self.index = 0
        self.round = 1
        self.looping = False
        self.sounding = False
        self.phase = "ready"
        self.gap_ms = 1400
        self.volume = .85
        self.calls = []

    @property
    def current(self):
        return self.items[self.index]

    def start(self):
        self.calls.append("start")
        self.looping = self.sounding = True
        self.phase = "sounding"
        self.changed.emit()

    def pause(self):
        self.calls.append("pause")
        self.looping = self.sounding = False
        self.phase = "paused"
        self.changed.emit()

    def toggle(self):
        self.calls.append("toggle")
        if self.looping or self.sounding:
            self.pause()
        else:
            self.start()

    def replay(self):
        self.calls.append("replay")
        self.sounding = True
        self.phase = "sounding"
        self.changed.emit()

    def move(self, delta):
        self.calls.append(("move", delta))
        self.index = (self.index + delta) % len(self.items)
        self.sounding = True
        self.phase = "sounding"
        self.changed.emit()

    def set_group(self, kind):
        self.calls.append(("group", kind))
        self.items = self.all_items if kind == "all" else [item for item in self.all_items if item["category"] in (("vowel", "sign") if kind == "vowels" else ("consonant",))]
        self.index = 0
        self.round = 1
        self.changed.emit()

    def set_volume(self, volume):
        self.volume = volume

    def shutdown(self):
        self.calls.append("shutdown")
        self.sounding = self.looping = False


class WindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        self.saved = []
        for name, replacement in (
            ("SoundPlayer", RecordingPlayer),
            ("load_settings", lambda: dict(DEFAULTS)),
            ("save_settings", lambda settings: self.saved.append(dict(settings))),
        ):
            patcher = patch.object(window_module, name, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.window = window_module.MainWindow(controller=False)
        self.window.show()
        self.window.activateWindow()
        self.application.processEvents()
        self.addCleanup(self.close_window)
        self.window.player.calls.clear()

    def close_window(self):
        self.window.close()
        self.application.processEvents()
        self.window.deleteLater()
        self.application.processEvents()

    def key(self, key, modifiers=Qt.KeyboardModifier.NoModifier):
        target = self.application.focusWidget() or self.window
        QTest.keyClick(target, key, modifiers)
        self.application.processEvents()

    def test_menu_initial_focus_and_keyboard_navigation(self):
        self.assertEqual(self.window._screen, "home")
        self.assertFalse(self.window.player.looping)
        self.assertIs(self.application.focusWidget(), self.window._buttons[0])
        self.key(Qt.Key.Key_Down)
        self.assertIs(self.application.focusWidget(), self.window._buttons[1])
        self.key(Qt.Key.Key_Up)
        self.key(Qt.Key.Key_Return)
        self.assertEqual(self.window._screen, "practice")
        self.assertEqual(self.window.player.calls, ["start"])

    def test_opening_menu_pauses_without_advancing_and_resume_keeps_letter(self):
        self.window.resume()
        self.window.player.move(8)
        index = self.window.player.index
        self.key(Qt.Key.Key_Escape)
        self.assertEqual(self.window._screen, "home")
        self.assertEqual(self.window.player.index, index)
        self.assertFalse(self.window.player.looping)
        self.key(Qt.Key.Key_Return)
        self.assertEqual(self.window._screen, "practice")
        self.assertEqual(self.window.player.index, index)
        self.assertTrue(self.window.player.looping)

    def test_practice_hotkeys_route_to_player_and_pause_does_not_advance(self):
        self.window.resume()
        self.key(Qt.Key.Key_Right)
        self.assertEqual(self.window.player.index, 1)
        self.key(Qt.Key.Key_Space)
        self.assertFalse(self.window.player.looping)
        self.assertEqual(self.window.player.index, 1)
        self.key(Qt.Key.Key_R)
        self.assertIn("replay", self.window.player.calls)
        self.assertFalse(self.window.player.looping)
        self.key(Qt.Key.Key_Left)
        self.assertEqual(self.window.player.index, 0)
        old_gap = self.window.player.gap_ms
        self.key(Qt.Key.Key_Up)
        self.assertGreater(self.window.player.gap_ms, old_gap)
        self.key(Qt.Key.Key_Down)
        self.assertEqual(self.window.player.gap_ms, old_gap)

    def test_menu_settings_arrows_change_only_focused_setting(self):
        self.window.show_menu("playback")
        self.application.processEvents()
        self.key(Qt.Key.Key_Right)
        self.assertEqual(self.window.settings["group"], "vowels")
        self.assertEqual(len(self.window.player.items), 13)
        self.assertFalse(self.window.player.looping)
        self.key(Qt.Key.Key_Down)
        self.assertIs(self.application.focusWidget(), self.window.gap_button)
        self.key(Qt.Key.Key_Left)
        self.assertEqual(self.window.player.gap_ms, 1000)
        self.key(Qt.Key.Key_Down)
        self.key(Qt.Key.Key_Left)
        self.assertAlmostEqual(self.window.player.volume, .8)
        self.assertEqual(self.window.settings["gap_ms"], 1000)
        self.assertAlmostEqual(self.window.settings["volume"], .8)

    def test_menu_arrows_do_not_skip_letters_and_back_returns_home(self):
        self.window.player.index = 8
        self.key(Qt.Key.Key_Right)
        self.key(Qt.Key.Key_Left)
        self.assertEqual(self.window.player.index, 8)
        self.window.show_menu("controls")
        self.application.processEvents()
        self.key(Qt.Key.Key_Escape)
        self.assertEqual(self.window._screen, "home")
        self.assertEqual(self.window.player.index, 8)
        self.assertFalse(self.window.player.looping)

    def test_help_pauses_and_auto_repeat_does_not_toggle(self):
        self.window.resume()
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier, " ", True)
        self.application.sendEvent(self.window, event)
        self.assertTrue(self.window.player.looping)
        self.key(Qt.Key.Key_F1)
        self.assertEqual(self.window._screen, "controls")
        self.assertFalse(self.window.player.looping)

    def test_controller_routes_and_suppresses_duplicate_keyboard_input(self):
        self.window.resume()
        with patch.object(self.window, "isActiveWindow", return_value=True), patch.object(window_module.time, "monotonic", return_value=100.):
            self.window.controller_action("accept")
            self.assertFalse(self.window.player.looping)
            self.key(Qt.Key.Key_Space)
            self.assertFalse(self.window.player.looping)
        with patch.object(window_module.time, "monotonic", return_value=101.):
            self.key(Qt.Key.Key_Space)
            self.assertTrue(self.window.player.looping)
        with patch.object(self.window, "isActiveWindow", return_value=False):
            self.window.controller_action("right")
        self.assertEqual(self.window.player.index, 0)

    def test_enter_activates_focused_practice_button(self):
        self.window.resume()
        self.window.next_button.setFocus()
        self.key(Qt.Key.Key_Return)
        self.assertEqual(self.window.player.index, 1)
        self.assertTrue(self.window.player.looping)
        self.window.menu_button.setFocus()
        self.key(Qt.Key.Key_Return)
        self.assertEqual(self.window._screen, "home")
        self.assertFalse(self.window.player.looping)

    def test_minimum_size_keeps_transport_and_letter_visible(self):
        self.window.resume()
        self.window.resize(1, 1)
        self.application.processEvents()
        self.assertGreaterEqual(self.window.width(), 800)
        self.assertGreaterEqual(self.window.height(), 540)
        for widget in (self.window.glyph, self.window.play_button, self.window.prev_button, self.window.next_button, self.window.replay_button, self.window.menu_button):
            top_left = widget.mapTo(self.window, QPoint(0, 0))
            self.assertGreaterEqual(top_left.x(), 0)
            self.assertGreaterEqual(top_left.y(), 0)
            self.assertLessEqual(top_left.x() + widget.width(), self.window.width())
            self.assertLessEqual(top_left.y() + widget.height(), self.window.height())
            self.assertGreater(widget.width(), 0)
            self.assertGreater(widget.height(), 0)

    def test_close_persists_current_settings_without_touching_real_user_state(self):
        self.window.cycle_group(1)
        self.window.player.index = 5
        self.window.adjust_gap(1)
        self.window.adjust_volume(-1)
        self.window.close()
        self.assertEqual(len(self.saved), 1)
        self.assertEqual(self.saved[0]["group"], "vowels")
        self.assertEqual(self.saved[0]["letter_id"], self.window.player.current["id"])
        self.assertEqual(self.saved[0]["gap_ms"], self.window.player.gap_ms)
        self.assertEqual(self.saved[0]["volume"], self.window.player.volume)
        self.assertEqual(self.window.player.calls.count("shutdown"), 1)


if __name__ == "__main__":
    unittest.main()
