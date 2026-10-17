STYLE = '''
* { color: #f4f7fb; font-family: "Segoe UI"; }
QMainWindow, QWidget#root, QWidget#displayPage, QWidget#menuPage { background: #10141c; }
QFrame#letterPanel { background: #171d28; border: 2px solid #252e3d; border-radius: 14px; }
QFrame#letterPanel[playing="true"] { background: #1a2a3d; border: 3px solid #8ec5ff; }
QLabel { border: none; background: transparent; }
QLabel#title { font-size: 25px; font-weight: 650; }
QLabel#muted { color: #aeb9c9; font-size: 14px; }
QLabel#badge { color: #8ec5ff; background: #171d28; border: 1px solid #252e3d; border-radius: 10px; padding: 7px 12px; font-size: 13px; }
QLabel#menuTitle { font-size: 38px; font-weight: 700; }
QLabel#menuSubtitle { color: #aeb9c9; font-size: 16px; }
QLabel#helpText { color: #b7c4d6; font-size: 17px; line-height: 1.6; }
QLabel#error { color: #ffb6aa; font-size: 14px; }
QPushButton { background: #171d28; border: 2px solid #252e3d; border-radius: 12px; padding: 13px 18px; font-size: 18px; text-align: left; min-height: 28px; }
QPushButton:hover { border-color: #6f8097; }
QPushButton:focus { background: #252e3d; border: 3px solid #8ec5ff; padding: 12px 17px; }
QPushButton#primary { background: #24394f; border-color: #507ba1; }
QPushButton#transport { font-size: 16px; padding: 8px 13px; min-height: 22px; }
QProgressBar { border: 0; background: #252e3d; max-height: 3px; min-height: 3px; }
QProgressBar::chunk { background: #8ec5ff; }
QScrollArea, QWidget#menuContent { border: none; background: transparent; }
QScrollBar:vertical { background: #10141c; width: 10px; }
QScrollBar::handle:vertical { background: #39475b; border-radius: 4px; min-height: 35px; }
'''
