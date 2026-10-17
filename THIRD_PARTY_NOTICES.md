# Third-party notices

## Hindi recordings

“Pronouncing the Hindi Alphabet”, created by Mansi Bajaj, Hindi at the University of Texas at Austin.

Source: https://hindi.la.utexas.edu/resources/pronouncing-the-hindi-alphabet/

License: Creative Commons Attribution 4.0 International (CC BY 4.0), https://creativecommons.org/licenses/by/4.0/

The recordings were excerpted into individual character clips and peak-normalized. Each entry in assets/letters.json records the original filename and excerpt range. This independent adaptation is not endorsed by the creator or university.

## Font

Noto Sans Devanagari, Noto Project contributors, SIL Open Font License 1.1. The complete license is bundled in assets/fonts/OFL.txt.

## Runtime

- PySide6 6.11.1 / Qt for Python: LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only; https://www.qt.io/qt-for-python . Qt libraries remain separate dynamically loaded files in the one-folder release.
- pygame-ce 2.5.8 / SDL: LGPL-2.1 and SDL licenses; https://pyga.me/ . Used for optional controller input.
- PyInstaller 6.22.2: GPL-2.0-or-later with the PyInstaller exception (build tool); https://pyinstaller.org/ .
- Qt Multimedia uses the bundled FFmpeg 7.1.3 backend, which reports LGPL version 2.1 or later; its build configuration is preserved in `licenses/installed-runtime-versions.json`.

Runtime license texts, installed package metadata, and versioned upstream Qt attribution notices are included in the `licenses` folder (`_internal/licenses` in the packaged app). See its README and source manifests for their provenance.

The graphite UI and controller navigation code are adapted from the user's local Words project. Hindi Sounds uses its own files and application-state directory.
