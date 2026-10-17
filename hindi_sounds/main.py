from __future__ import annotations
import argparse
import json
import os
import sys
import tempfile
import traceback
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtGui import QFontDatabase, QIcon
from PySide6.QtWidgets import QApplication, QMessageBox
from .settings import asset_root, state_root

def run() -> int:
    parser=argparse.ArgumentParser(description='Offline Hindi letters and sounds')
    parser.add_argument('--windowed',action='store_true')
    parser.add_argument('--smoke-test',type=Path,metavar='REPORT_JSON')
    parser.add_argument('--screenshot-dir',type=Path)
    args=parser.parse_args()
    isolated=None
    if args.smoke_test or args.screenshot_dir:
        isolated=tempfile.TemporaryDirectory(prefix='hindi-sounds-check-')
        os.environ['HINDI_SOUNDS_APPDATA_DIR']=isolated.name
    app=QApplication(sys.argv[:1]); app.setApplicationName('Hindi Sounds'); app.setOrganizationName('HindiSoundsApp')
    QFontDatabase.addApplicationFont(str(asset_root()/'fonts'/'hindi.ttf'))
    app.setWindowIcon(QIcon(str(asset_root()/'hindi-sounds.ico')))
    try:
        from .window import MainWindow
        window=MainWindow(controller=not bool(args.smoke_test or args.screenshot_dir))
        if args.windowed or args.smoke_test or args.screenshot_dir: window.settings['window_mode']='windowed'
        window.apply_window_mode()
        if args.smoke_test:
            report={'success':False,'played':[],'sound_events':0,'gap_events':0,'errors':[]}
            window.player.set_volume(0.)
            window.player.gap_ms=100
            window.player.index=len(window.player.items)-2
            done=False
            def finish(success, message=''):
                nonlocal done
                if done:return
                done=True;report['success']=success
                if message:report['errors'].append(message)
                args.smoke_test.parent.mkdir(parents=True,exist_ok=True)
                args.smoke_test.write_text(json.dumps(report,indent=2),encoding='utf-8')
                window.close();app.exit(0 if success else 1)
            def observe():
                if done:return
                if window.player.sounding:
                    current=window.player.current['id']
                    if not report['played'] or report['played'][-1]!=current:report['played'].append(current)
                    report['sound_events']+=1
                if window.player.phase=='gap':
                    report['gap_events']+=1
                    if report['played']==['45','46','01']:finish(True)
            window.player.changed.connect(observe)
            window.player.error.connect(lambda error:finish(False,error))
            QTimer.singleShot(100,window.resume)
            QTimer.singleShot(20000,lambda:finish(False,'Audio playback or looping timed out'))
        elif args.screenshot_dir:
            target=args.screenshot_dir;target.mkdir(parents=True,exist_ok=True)
            window.player.set_volume(0.)
            captured=False
            def capture_sound():
                nonlocal captured
                if window.player.sounding and not captured:
                    captured=True
                    QTimer.singleShot(90,save_active)
            def save_active():
                window.grab().save(str(target/'practice-active.png'))
                window.player.pause()
                QTimer.singleShot(80,save_paused)
            def save_paused():
                window.grab().save(str(target/'practice-paused.png'))
                window.show_menu('home');QTimer.singleShot(80,save_home)
            def save_home():
                window.grab().save(str(target/'menu.png'))
                window.show_menu('playback');QTimer.singleShot(80,save_settings)
            def save_settings():
                window.grab().save(str(target/'playback.png'))
                window.resize(800,540);window.resume();QTimer.singleShot(100,save_small)
            def save_small():
                window.grab().save(str(target/'practice-small.png'));window.close()
            window.player.changed.connect(capture_sound)
            QTimer.singleShot(150,window.resume)
            QTimer.singleShot(15000,window.close)
        result=app.exec()
    except Exception as exc:
        detail=traceback.format_exc()
        root=state_root();root.mkdir(parents=True,exist_ok=True);(root/'startup-error.txt').write_text(detail,encoding='utf-8')
        if args.smoke_test:
            args.smoke_test.parent.mkdir(parents=True,exist_ok=True)
            args.smoke_test.write_text(json.dumps({'success':False,'error':detail}),encoding='utf-8')
        else:QMessageBox.critical(None,'Hindi Sounds could not start',f'{exc}\n\nDetails: {root / "startup-error.txt"}')
        result=1
    if isolated:isolated.cleanup()
    return result

if __name__=='__main__':raise SystemExit(run())
