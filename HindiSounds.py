"""Desktop entry point, including diagnostics for early runtime import failures."""
if __name__ == '__main__':
    try:
        from hindi_sounds.main import run
        raise SystemExit(run())
    except Exception:
        import os
        import traceback
        from pathlib import Path

        try:
            folder = Path(os.environ.get('HINDI_SOUNDS_APPDATA_DIR') or
                          Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'HindiSoundsApp')
            folder.mkdir(parents=True, exist_ok=True)
            (folder / 'startup-error.txt').write_text(traceback.format_exc(), encoding='utf-8')
        except OSError:
            pass
        raise
