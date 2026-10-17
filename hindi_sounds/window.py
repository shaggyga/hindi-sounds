from __future__ import annotations
import json
import time
from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QFont, QFontMetricsF
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow, QProgressBar, QPushButton, QScrollArea, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget
from .controller import ControllerManager
from .player import SoundPlayer
from .settings import GAPS, asset_root, load_settings, save_settings
from .theme import STYLE

class MainWindow(QMainWindow):
    def __init__(self, *, controller=True):
        super().__init__()
        self.settings = load_settings()
        items = json.loads((asset_root() / 'letters.json').read_text(encoding='utf-8-sig'))
        self.player = SoundPlayer(items, asset_root(), self)
        self.player.set_group(self.settings['group'])
        self.player.index = next((i for i, item in enumerate(self.player.items) if item['id'] == self.settings['letter_id']), 0)
        self.player.gap_ms = self.settings['gap_ms']
        self.player.set_volume(self.settings['volume'])
        self._screen = 'home'
        self._started = False
        self._closing = False
        self._buttons = []
        self._option_steps = {}
        self._suppress_until = {}
        self.setWindowTitle('Hindi Sounds')
        self.setMinimumSize(800, 540)
        self.resize(1280, 800)
        self.setStyleSheet(STYLE)
        self.stack = QStackedWidget()
        self.stack.setObjectName('root')
        self.setCentralWidget(self.stack)
        self._build_display()
        self._build_menu()
        self.player.changed.connect(self.refresh)
        self.player.error.connect(self.show_error)
        self.controller = ControllerManager(self) if controller else None
        if self.controller:
            self.controller.action.connect(self.controller_action)
        QApplication.instance().installEventFilter(self)
        self.show_menu('home')
        self.refresh()

    def _button(self, text, callback, *, name=''):
        button = QPushButton(text)
        if name: button.setObjectName(name)
        button.clicked.connect(callback)
        return button

    def _build_display(self):
        self.display = QWidget(); self.display.setObjectName('displayPage')
        layout = QVBoxLayout(self.display); layout.setContentsMargins(24, 20, 24, 16); layout.setSpacing(14)
        top = QHBoxLayout()
        title = QLabel('Hindi Sounds'); title.setObjectName('title')
        self.pause_badge = QLabel('READY'); self.pause_badge.setObjectName('badge')
        self.counter = QLabel('01 / 46'); self.counter.setObjectName('badge')
        top.addWidget(title, 1); top.addWidget(self.pause_badge); top.addSpacing(10); top.addWidget(self.counter)
        layout.addLayout(top)
        self.panel = QFrame(); self.panel.setObjectName('letterPanel'); self.panel.setProperty('playing', False)
        panel_layout = QVBoxLayout(self.panel); panel_layout.setContentsMargins(26, 20, 26, 20)
        card_top = QHBoxLayout()
        self.category = QLabel('VOWEL'); self.category.setObjectName('muted')
        self.round = QLabel('ROUND 01'); self.round.setObjectName('muted')
        card_top.addWidget(self.category); card_top.addStretch(); card_top.addWidget(self.round)
        panel_layout.addLayout(card_top)
        self.glyph = QLabel('अ'); self.glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.glyph.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.glyph.setMinimumSize(0, 0)
        self.glyph.setAccessibleName('Current Hindi letter')
        panel_layout.addWidget(self.glyph, 1)
        self.sound_status = QLabel('Press Play to begin'); self.sound_status.setObjectName('muted'); self.sound_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(self.sound_status)
        layout.addWidget(self.panel, 1)
        self.progress = QProgressBar(); self.progress.setTextVisible(False); self.progress.setAccessibleName('Alphabet progress')
        layout.addWidget(self.progress)
        self.error_label = QLabel(); self.error_label.setObjectName('error'); self.error_label.setWordWrap(True); self.error_label.hide()
        layout.addWidget(self.error_label)
        controls = QHBoxLayout(); controls.setSpacing(10)
        self.status = QLabel(); self.status.setObjectName('muted'); controls.addWidget(self.status, 1)
        self.prev_button = self._button('Previous', lambda: self.player.move(-1), name='transport')
        self.play_button = self._button('Play', self.player.toggle, name='transport')
        self.replay_button = self._button('Replay', self.player.replay, name='transport')
        self.next_button = self._button('Next', lambda: self.player.move(1), name='transport')
        self.menu_button = self._button('Menu', lambda: self.show_menu('home'), name='transport')
        for button in (self.prev_button, self.play_button, self.replay_button, self.next_button, self.menu_button): controls.addWidget(button)
        layout.addLayout(controls)
        self.prompts = QLabel('Space / A  play-pause    •    Left / Right  letter    •    Up / Down  pause length    •    R / X  replay    •    Esc / Start  menu')
        self.prompts.setObjectName('muted'); self.prompts.setAlignment(Qt.AlignmentFlag.AlignCenter); self.prompts.setWordWrap(True)
        layout.addWidget(self.prompts)
        self.stack.addWidget(self.display)

    def _build_menu(self):
        self.menu_page = QWidget(); self.menu_page.setObjectName('menuPage')
        outer = QVBoxLayout(self.menu_page); outer.setContentsMargins(24, 20, 24, 16)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.menu_content = QWidget(); self.menu_content.setObjectName('menuContent')
        self.menu_layout = QVBoxLayout(self.menu_content); self.menu_layout.setContentsMargins(0, 12, 0, 12); self.menu_layout.setSpacing(10)
        self.scroll.setWidget(self.menu_content); outer.addWidget(self.scroll, 1)
        hint = QLabel('Up / Down  navigate    •    Enter / A  select    •    Left / Right  change setting    •    Esc / B  back')
        hint.setWordWrap(True); hint.setObjectName('muted'); hint.setAlignment(Qt.AlignmentFlag.AlignCenter); outer.addWidget(hint)
        self.stack.addWidget(self.menu_page)

    def show_menu(self, screen='home'):
        self.player.pause()
        self._screen = screen
        self.stack.setCurrentWidget(self.menu_page)
        self._buttons = []; self._option_steps = {}
        while self.menu_layout.count():
            item = self.menu_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        title = QLabel({'home':'Hindi Sounds', 'playback':'Playback', 'display':'Display', 'controls':'Controls', 'credits':'About this lesson'}[screen]); title.setObjectName('menuTitle')
        subtitle = QLabel({'home':'One letter. One sound. A continuous loop.', 'playback':'Leave a little space to listen and repeat.', 'display':'Choose how the practice screen fills your display.', 'controls':'Use a keyboard, mouse, or controller.', 'credits':'46 core Hindi characters · recorded pronunciation · works offline'}[screen]); subtitle.setObjectName('menuSubtitle'); subtitle.setWordWrap(True)
        for label in (title, subtitle): label.setMinimumWidth(550); label.setMaximumWidth(760); self.menu_layout.addWidget(label, 0, Qt.AlignmentFlag.AlignHCenter)
        self.menu_layout.addSpacing(12)
        if screen == 'home':
            self.add_menu_button('Resume sounds' if self._started else 'Start sounds', self.resume, primary=True)
            self.add_menu_button('Restart from the first letter', self.restart)
            self.add_menu_button('Playback settings', lambda: self.show_menu('playback'))
            self.add_menu_button('Display settings', lambda: self.show_menu('display'))
            self.add_menu_button('Controls', lambda: self.show_menu('controls'))
            self.add_menu_button('About && audio credits', lambda: self.show_menu('credits'))
            self.add_menu_button('Exit', self.close)
        elif screen == 'playback':
            self.group_button = self.add_menu_button('', lambda: self.cycle_group(1), step=self.cycle_group)
            self.gap_button = self.add_menu_button('', lambda: self.adjust_gap(1), step=self.adjust_gap)
            self.volume_button = self.add_menu_button('', lambda: self.adjust_volume(1), step=self.adjust_volume)
            self.update_option_labels()
        elif screen == 'display':
            self.window_button = self.add_menu_button('', self.cycle_window, step=lambda delta:self.cycle_window(delta))
            self.update_option_labels()
        elif screen == 'controls':
            self.add_text('During practice\n\nSpace / A — play or pause\n← / → or D-pad — previous / next letter\n↑ / ↓ — longer / shorter pause between sounds\nR / X — replay the current sound\nEsc / Start — open menu\nF1 / View — show these controls\nF11 — cycle windowed, borderless, and full screen\n\nIn menus\n\n↑ / ↓ — move between buttons\n← / → — change the focused setting\nEnter / A — select · Esc / B — go back\n\nOpening a menu or minimizing the app pauses playback.\nResume plays the current sound from the beginning.')
        elif screen == 'credits':
            self.add_text('This first lesson includes 11 independent vowels, two vowel signs shown with अ, and 33 basic consonants. Consonants include their inherent vowel. Additional nukta letters and conjuncts are not included.\n\nAudio: Mansi Bajaj, Hindi at the University of Texas at Austin — “Pronouncing the Hindi Alphabet”. Licensed CC BY 4.0. Recordings were split into individual clips and normalized.\n\nhindi.la.utexas.edu/resources/pronouncing-the-hindi-alphabet/\ncreativecommons.org/licenses/by/4.0/\n\nNoto Sans Devanagari is distributed under SIL OFL 1.1.\nSee THIRD_PARTY_NOTICES.md in the app folder for details.')
        if screen != 'home': self.add_menu_button('Back', lambda:self.show_menu('home'))
        self.menu_layout.addStretch()
        QTimer.singleShot(0, lambda:self._focus_button(0))

    def add_text(self, text):
        text = text.replace('← / →', 'Left / Right').replace('↑ / ↓', 'Up / Down').replace('→', 'Right').replace('←', 'Left')
        label = QLabel(text); label.setObjectName('helpText'); label.setWordWrap(True); label.setMinimumWidth(550); label.setMaximumWidth(760)
        self.menu_layout.addWidget(label, 0, Qt.AlignmentFlag.AlignHCenter)

    def add_menu_button(self, text, callback, *, primary=False, step=None):
        button = self._button(text, callback, name='primary' if primary else '')
        button.setMinimumWidth(550); button.setMaximumWidth(760)
        self.menu_layout.addWidget(button, 0, Qt.AlignmentFlag.AlignHCenter)
        self._buttons.append(button)
        if step: self._option_steps[button] = step
        return button

    def _focus_button(self, index):
        if not self._buttons: return
        button = self._buttons[index % len(self._buttons)]
        button.setFocus(); self.scroll.ensureWidgetVisible(button, 0, 30)

    def update_option_labels(self):
        if self._screen == 'playback':
            group = {'all':'All 46 characters', 'vowels':'Vowels & signs · 13', 'consonants':'Consonants · 33'}[self.settings['group']]
            self.group_button.setText(f'Letters                      {group}')
            self.gap_button.setText(f'Pause between sounds         {self.player.gap_ms / 1000:g} seconds')
            self.volume_button.setText(f'Volume                       {round(self.player.volume * 100)}%')
        if self._screen == 'display': self.window_button.setText('Window mode                  ' + self.settings['window_mode'].title())

    def cycle_group(self, delta):
        groups = ('all', 'vowels', 'consonants')
        self.settings['group'] = groups[(groups.index(self.settings['group']) + delta) % len(groups)]
        self.player.set_group(self.settings['group']); self.update_option_labels()

    def adjust_gap(self, delta):
        index = min(range(len(GAPS)), key=lambda i:abs(GAPS[i]-self.player.gap_ms))
        self.player.gap_ms = GAPS[max(0, min(len(GAPS)-1, index+delta))]
        self.settings['gap_ms'] = self.player.gap_ms; self.refresh(); self.update_option_labels()

    def adjust_volume(self, delta):
        self.player.set_volume(max(0., min(1., round(self.player.volume + .05 * delta, 2))))
        self.settings['volume'] = self.player.volume; self.update_option_labels()

    def cycle_window(self, delta=1):
        modes = ('windowed', 'borderless', 'fullscreen')
        self.settings['window_mode'] = modes[(modes.index(self.settings['window_mode'])+delta)%len(modes)]
        self.apply_window_mode(); self.update_option_labels()

    def apply_window_mode(self):
        mode = self.settings['window_mode']
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, mode == 'borderless')
        if mode == 'fullscreen': self.showFullScreen()
        elif mode == 'borderless': self.showMaximized()
        else: self.showNormal()

    def resume(self):
        self._screen = 'practice'; self._started = True
        self.stack.setCurrentWidget(self.display); self.display.setFocus()
        self.player.start()

    def restart(self):
        self.player.pause(); self.player.index = 0; self.player.round = 1; self.resume()

    def refresh(self):
        item = self.player.current
        self.glyph.setText(item['letter'])
        self.counter.setText(f'{self.player.index+1:02} / {len(self.player.items)}')
        self.round.setText(f'ROUND {self.player.round:02}')
        self.category.setText({'vowel':'VOWEL', 'sign':'VOWEL SIGN', 'consonant':'CONSONANT'}[item['category']])
        active = self.player.looping or self.player.phase in ('sounding','loading')
        self.play_button.setText('Pause' if active else 'Play')
        self.pause_badge.setText('LOOPING' if self.player.looping else 'LISTEN' if self.player.sounding else 'PAUSED' if self._started else 'READY')
        self.sound_status.setText({'ready':'Press Play to begin', 'loading':'Loading sound…', 'sounding':'Listen', 'gap':'Repeat', 'paused':'Paused', 'error':'Sound unavailable — press Replay to try again'}[self.player.phase])
        if self.panel.property('playing') != self.player.sounding:
            self.panel.setProperty('playing', self.player.sounding)
            self.panel.style().unpolish(self.panel); self.panel.style().polish(self.panel); self.panel.update()
        self.glyph.setStyleSheet('color: #8ec5ff;' if self.player.sounding else 'color: #f4f7fb;')
        self.progress.setRange(0, len(self.player.items)); self.progress.setValue(self.player.index+1)
        self.status.setText(f'{self.player.gap_ms/1000:g}s pause')
        if self.player.phase != 'error': self.error_label.hide()
        self._fit_glyph()

    def show_error(self, message):
        self.error_label.setText(message); self.error_label.show()

    def _fit_glyph(self):
        font = QFont('Noto Sans Devanagari'); font.setFamilies(['Noto Sans Devanagari', 'Nirmala UI', 'Mangal'])
        width, height = max(10,self.glyph.width()-50), max(10,self.glyph.height()-30)
        low, high, best = 32, min(440, int(height*.85)), 32
        while low <= high:
            mid=(low+high)//2; font.setPixelSize(mid); bounds=QFontMetricsF(font).boundingRect(self.glyph.text())
            if bounds.width()<=width and bounds.height()<=height: best=mid; low=mid+1
            else: high=mid-1
        font.setPixelSize(best); self.glyph.setFont(font)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self,'glyph'): self._fit_glyph()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type()==QEvent.Type.WindowStateChange and self.isMinimized() and hasattr(self,'player'): self.player.pause()

    def controller_action(self, action):
        if not self.isActiveWindow(): return
        self._suppress_until[action] = time.monotonic()+.13
        self.dispatch(action)

    def dispatch(self, action):
        if self._screen != 'practice':
            focused = QApplication.focusWidget()
            if action in ('up','down'):
                index=self._buttons.index(focused) if focused in self._buttons else 0
                self._focus_button(index+(1 if action=='down' else -1))
            elif action in ('left','right') and focused in self._option_steps: self._option_steps[focused](-1 if action=='left' else 1)
            elif action=='accept' and focused in self._buttons: focused.click()
            elif action=='back': self.resume() if self._screen=='home' else self.show_menu('home')
            elif action=='menu': self.resume()
            elif action=='help': self.show_menu('controls')
            return
        callbacks={'accept':self.player.toggle, 'left':lambda:self.player.move(-1), 'right':lambda:self.player.move(1), 'page_left':lambda:self.player.move(-1), 'page_right':lambda:self.player.move(1), 'up':lambda:self.adjust_gap(1), 'down':lambda:self.adjust_gap(-1), 'extra':self.player.replay, 'menu':lambda:self.show_menu('home'), 'back':lambda:self.show_menu('home'), 'help':lambda:self.show_menu('controls')}
        if action in callbacks: callbacks[action]()

    def eventFilter(self, watched, event):
        if event.type()!=QEvent.Type.KeyPress or not isinstance(watched,QWidget) or watched.window() is not self: return False
        key=event.key()
        if event.modifiers() & (Qt.KeyboardModifier.ControlModifier|Qt.KeyboardModifier.AltModifier|Qt.KeyboardModifier.MetaModifier): return False
        if key==Qt.Key.Key_F11:
            if not event.isAutoRepeat(): self.cycle_window()
            return True
        if key in (Qt.Key.Key_Return,Qt.Key.Key_Enter) and self._screen=='practice':
            focused=QApplication.focusWidget()
            if isinstance(focused,QPushButton) and not event.isAutoRepeat():
                focused.click()
                return True
        keys={Qt.Key.Key_Space:'accept', Qt.Key.Key_Return:'accept', Qt.Key.Key_Enter:'accept', Qt.Key.Key_Left:'left', Qt.Key.Key_Right:'right', Qt.Key.Key_Up:'up', Qt.Key.Key_Down:'down', Qt.Key.Key_Escape:'back', Qt.Key.Key_R:'extra', Qt.Key.Key_X:'extra', Qt.Key.Key_F1:'help'}
        action=keys.get(key)
        if not action: return False
        if event.isAutoRepeat() and action not in ('up','down','left','right'): return True
        if time.monotonic()>=self._suppress_until.get(action,0): self.dispatch(action)
        return True

    def closeEvent(self, event):
        if not self._closing:
            self._closing=True
            self.settings.update(letter_id=self.player.current['id'], gap_ms=self.player.gap_ms, volume=self.player.volume)
            self.player.shutdown()
            if self.controller: self.controller.shutdown()
            QApplication.instance().removeEventFilter(self)
            try: save_settings(self.settings)
            except OSError: pass
        event.accept()
