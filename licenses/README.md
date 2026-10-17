# Runtime license texts and provenance

This folder accompanies Hindi Sounds. It contains full third-party license texts and upstream attribution records. The application does not claim ownership of these components.

## Installed package documents

- pygame-ce-LGPL-2.1.txt is the complete LGPL 2.1 text copied verbatim from the installed pygame-ce 2.5.8 documentation.
- PyInstaller-COPYING.txt is copied verbatim from installed PyInstaller 6.22.2 and includes its bootloader exception.
- The *installed-METADATA.txt files preserve the installed package authors, versions, license declarations and source links for PySide6, PySide6 Addons, PySide6 Essentials, Shiboken6 and pygame-ce.
- LicenseRef-Qt-Commercial-installed.txt is a verbatim installed upstream file, retained as part of its published licensing choices; its inclusion does not assert possession of a commercial Qt license.
- installed-notice-sources.json records the package-relative source of each copied document within the build environment.

## Versioned upstream supplements

The installed PySide6 wheels did not include full LGPL/GPL texts or external Qt/FFmpeg attribution notices. Those texts were supplemented from official upstream repositories:

- PySide6-6.11.1 contains the complete LICENSES directory from pyside/pyside-setup tag 6.11.1.
- Qt-6.11.1 contains the complete LICENSES directory from qt/qtbase tag v6.11.1.
- Qt-attributions contains versioned Qt 6.11.1 attribution JSON, referenced license files and module LICENSES directories. This preserves an upstream notice corpus, including records for optional features; inclusion of a notice does not indicate that its component or feature is used by Hindi Sounds.
- SDL notices are the complete upstream notices for SDL 2.32.10, SDL_image 2.8.12, SDL_mixer 2.8.2 and SDL_ttf 2.24.0, corresponding to versions reported by the installed runtime.
- FFmpeg-7.1.3 contains the upstream license summary and full license texts from tag n7.1.3. The installed avutil DLL reports LGPL version 2.1 or later. Its exact version and configuration are recorded in installed-runtime-versions.json. The matching Qt 6.11.1 FFmpeg attribution includes its developer copyright and additional third-party license identifiers.

upstream-notice-sources.json and qt-attribution-sources.json record original upstream URLs, file sizes and SHA-256 hashes. These records distinguish documents copied from the installed wheels from documents obtained from the matching official source releases.
