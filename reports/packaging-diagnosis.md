# Packaged QtCore startup failure: confirmed ICU DLL collision

Date: 2026-10-16

## Failure and environment

The source application loaded successfully using Python 3.12.10 and PySide6 6.11.1 in the build virtual environment. The PyInstaller 6.22.2 collected executable failed at the first `PySide6.QtCore` import with “The specified procedure could not be found” (Windows error 127), before controller or pygame imports.

Diagnosis was read-only. Neither the Words project nor the collected release was modified during investigation.

## Exact incompatible dependency

`_internal/PySide6/Qt6Core.dll` imports 20 **unversioned** function names from `icuuc.dll`, including:

- `ucnv_open`, `ucnv_close`, `ucnv_reset`
- `ucnv_fromUnicode`, `ucnv_toUnicode`
- `ucnv_getName`, `ucnv_getMaxCharSize`
- `UCNV_TO_U_CALLBACK_SUBSTITUTE`, `UCNV_FROM_U_CALLBACK_SUBSTITUTE`

The collected `_internal/icuuc.dll` was ICU 78.3 from the Codex Poppler runtime. It exports version-suffixed names such as `ucnv_open_78` and `u_charDirection_78`; **all 20 exact ICU symbols required by Qt6Core were absent**.

The system DLL `C:/Windows/System32/icuuc.dll` exports all 20 required names without version suffixes.

`build/HindiSounds/Analysis-00.toc` recorded the incorrectly harvested source at the original lines 1384–1385:

```
<external-runtime>/dependencies/native/poppler/Library/bin/icuuc.dll
```

Its dependent `icudt78.dll` came from the same directory. The environment PATH also caused unrelated API-set and UCRT DLLs to be harvested from the Codex libheif runtime. These paths do not belong in this application's build environment.

## Reproduction isolating the cause

Two fresh Python subprocesses used the same packaged Qt6Core file and set the DLL search directory to the package `_internal` directory. Neither changed any file.

1. Load packaged Qt6Core directly: **failed with Windows error 127**.
2. First load `C:/Windows/System32/icuuc.dll` by absolute path, then load the same packaged Qt6Core: **succeeded**.

The key operations were:

```python
ctypes.windll.kernel32.SetDllDirectoryW(str(internal))
# Only in the successful subprocess:
ctypes.WinDLL(r"C:\Windows\System32\icuuc.dll")
ctypes.WinDLL(str(internal / "PySide6" / "Qt6Core.dll"), winmode=8)
```

This isolates the ICU name collision rather than inferring it from DLL version numbers.

## MSVC runtime versions were checked

The root package contains VCRUNTIME 14.42, while PySide6 and shiboken6 directories contain runtime 14.44. This difference was investigated with PE import/export tables. All requested VCRUNTIME/MSVCP exports were present in the applicable copies, including `__CxxFrameHandler4`. The checked importers were Qt6Core, pyside6.abi3, shiboken6.abi3, and MSVCP140, MSVCP140_1, and MSVCP140_2. No missing MSVC export explained this failure.

## Packaging correction

Rebuild with PATH restricted to the selected Python environment and Windows system directories, excluding the Codex Poppler/libheif/native directories. Before collection, exclude `icuuc.dll` and `icudt*.dll` from `a.binaries`. The application targets the installed Windows 10 environment, whose system ICU satisfies Qt's imports. Do not redistribute the unrelated Poppler ICU under the same DLL name.

After rebuilding:

```
python reports/check_bundle.py
```

The audit rejects bundled ICU DLLs and validates the 46 distinct WAV recordings referenced by the packaged manifest. A successful audit is a static packaging check; the packaged application's real-audio smoke test remains necessary to confirm startup, decoding, and looping.
