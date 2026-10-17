# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
project=Path(SPECPATH)
a=Analysis([str(project/'HindiSounds.py')],pathex=[str(project)],binaries=[],datas=[(str(project/'assets'),'assets'),(str(project/'THIRD_PARTY_NOTICES.md'),'.')],hiddenimports=['pygame._sdl2.controller'],hookspath=[],hooksconfig={},runtime_hooks=[],excludes=['PySide6.QtWebEngineCore','PySide6.QtWebEngineWidgets','PySide6.QtWebEngineQuick','PySide6.QtQml','PySide6.QtQuick','PySide6.QtPdf','PySide6.QtPdfWidgets','tkinter','pytest','numpy','PIL'],noarchive=False,optimize=1)
# This Qt build imports the unversioned ICU API provided by Windows 10/11.
# PATH may contain another application's ICU DLL with version-suffixed exports
# (e.g. Poppler's ICU 78). Bundling that DLL breaks QtCore at startup.
# VirtualKeyboard is unused by this widgets-only app; omit its optional plugin.
a.binaries = [entry for entry in a.binaries
              if Path(entry[0]).name.lower() not in
              {'icuuc.dll', 'qt6virtualkeyboard.dll', 'qtvirtualkeyboardplugin.dll'}
              and not Path(entry[0]).name.lower().startswith('icudt')]
if (project/'licenses').is_dir():
    a.datas += [(str(Path('licenses')/path.relative_to(project/'licenses')), str(path), 'DATA')
                for path in (project/'licenses').rglob('*') if path.is_file()]
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='Hindi Sounds',debug=False,bootloader_ignore_signals=False,strip=False,upx=False,console=False,disable_windowed_traceback=False,icon=[str(project/'assets'/'hindi-sounds.ico')])
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='Hindi Sounds')
