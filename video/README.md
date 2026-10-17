# Hindi Sounds video

`Hindi-Sounds.mp4` is the standalone video companion to Hindi Sounds. It contains one complete round of 46 core Hindi letters and signs, with each letter highlighted while its recorded sound plays. Practice cards contain no romanization or vocabulary.

- 1920 × 1080, 30 fps, H.264 with AAC mono audio, MP4 fast start.
- Duration: 1 minute 58.93 seconds.
- Each letter has a 0.5-second silent lead, its pronunciation, then 1 second of silence.
- Highlights share the audio clock; the frame rounding adds at most 30 ms to a highlight.
- Intro: 4 seconds. Outro: 4 seconds. Credits: 9 seconds.

## Source audio

Pronunciation audio: Mansi Bajaj, Hindi at the University of Texas at Austin.

Source: https://hindi.la.utexas.edu/resources/pronouncing-the-hindi-alphabet/

License: Creative Commons Attribution 4.0 International (CC BY 4.0), https://creativecommons.org/licenses/by/4.0/

The recordings were excerpted and volume-normalized. Full attribution is also embedded in the video credits and MP4 metadata. The application and video share `../assets/letters.json` and `../assets/audio/`; the manifest records each original source file and excerpt interval.

## Rebuild and verify

Use Windows with Python 3.12 or 3.13 and Node.js 20 or later. From this directory, install the video dependencies and Chromium:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
npm install
npx playwright install chromium
.venv/Scripts/python.exe build_video.py --check
.venv/Scripts/python.exe build_video.py
.venv/Scripts/python.exe verify_video.py
```

`--check` validates all source recordings, FFmpeg, and a headless render without changing the existing MP4 or other output files. The full build overwrites `Hindi-Sounds.mp4` and regenerates its frames, audio, and timeline report. Run verification after a build so its generated reference frames and timeline are present.

The renderer uses Windows Nirmala UI for proper Devanagari shaping and Segoe UI for labels. These fonts preserve the supplied video's appearance. Other operating systems require compatible fonts and may render differently. The scripts locate all project files relative to themselves, so they can also be run from another working directory.

Node.js is discovered on `PATH`; optionally set `HINDI_SOUNDS_NODE` to its full executable path. Playwright uses its installed Chromium by default. Optionally set `HINDI_SOUNDS_BROWSER_PATH` to an existing Chromium-based browser executable, such as Microsoft Edge. Python uses `imageio-ffmpeg` for the encoder and `numpy`/Pillow for verification. No machine-specific runtime paths are required.

`validation.json` reports full video decode, matching of all 46 encoded letter frames, and correlation of every decoded pronunciation with its original PCM clip at the intended start time. `video-contact-sheet.jpg` shows all 46 encoded cards.
