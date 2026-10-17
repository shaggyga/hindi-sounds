"""Render a reproducible Hindi flashcard lesson with frame-aligned sound highlights."""
from pathlib import Path
import argparse, json, math, os, shutil, subprocess, wave
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'assets'
DIST = ROOT
NODE = os.environ.get('HINDI_SOUNDS_NODE') or shutil.which('node')
if not NODE:
    raise SystemExit('Node.js was not found. Add node to PATH or set HINDI_SOUNDS_NODE to its executable.')
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FPS, SR = 30, 44100
INTRO_SECONDS, OUTRO_SECONDS, CREDIT_SECONDS = 4, 4, 9

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--check', action='store_true', help='Check source audio and the renderer without writing files or rebuilding the MP4')
args = parser.parse_args()
items = json.loads((SOURCE/'letters.json').read_text(encoding='utf-8-sig'))
if args.check:
    for item in items:
        with wave.open(str(SOURCE/item['audio']), 'rb') as wav:
            if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 2, SR) or wav.getnframes() <= 0:
                raise ValueError(f"Invalid source recording: {item['audio']}")
    subprocess.run([FFMPEG, '-version'], check=True, stdout=subprocess.DEVNULL)
    subprocess.run([str(NODE), str(ROOT/'render_frames.cjs'), '--check'], check=True)
    print(f'Build entry check passed for {len(items)} recordings; no output files were changed.')
    raise SystemExit(0)
categories = {'vowel':'Vowel', 'consonant':'Consonant', 'sign':'Vowel sign', 'special':'Additional letter', 'conjunct':'Conjunct'}
data = {'items':[{**item, 'category':categories.get(item['category'],item['category'].replace('-',' ').title()), 'romanization':item.get('roman',item.get('romanization',''))} for item in items],
        'attribution':{
            'credit':'Pronunciation audio: Mansi Bajaj · Hindi at the University of Texas at Austin.',
            'adaptation':'Audio excerpts have been trimmed and volume-normalized for this lesson.',
            'url':'hindi.la.utexas.edu/resources/pronouncing-the-hindi-alphabet/',
            'license':'Licensed under Creative Commons Attribution 4.0 International (CC BY 4.0).'
        }}
(ROOT/'video-data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
subprocess.run([str(NODE),str(ROOT/'render_frames.cjs')],check=True)

# Frames and audio use the same integer frame clock. Each silent lead is 0.5 s;
# the pronunciation is highlighted for its entire duration, followed by 1 s rest.
segments=[]
timeline=[]
pcm=bytearray()
clock=0
def segment(file, frames, audio_bytes=None):
    global clock
    samples = frames * SR // FPS
    payload = audio_bytes or b''
    if len(payload) > samples*2:
        raise ValueError('Audio longer than segment')
    pcm.extend(payload)
    pcm.extend(b'\0'*(samples*2-len(payload)))
    segments.append((file, frames/FPS))
    clock+=frames

segment('intro.png',INTRO_SECONDS*FPS)
for i,item in enumerate(items):
    prefix=f'{i:02d}'
    segment(f'{prefix}-idle.png',15)
    audio_start=clock/FPS
    with wave.open(str(SOURCE/item['audio']),'rb') as wav:
        assert (wav.getnchannels(),wav.getsampwidth(),wav.getframerate())==(1,2,SR)
        samples=wav.getnframes()
        clip=wav.readframes(samples)
    nframes=math.ceil(samples/SR*FPS)
    segment(f'{prefix}-active.png',nframes,clip)
    timeline.append({'letter':item['letter'],'id':item['id'],'audioStart':audio_start,'audioEnd':audio_start+samples/SR,'highlightEnd':clock/FPS,'source':item['audio']})
    segment(f'{prefix}-idle.png',FPS)
segment('outro.png',OUTRO_SECONDS*FPS)
segment('credits.png',CREDIT_SECONDS*FPS)

with wave.open(str(ROOT/'soundtrack.wav'),'wb') as wav:
    wav.setparams((1,2,SR,0,'NONE','not compressed'))
    wav.writeframes(pcm)
lines=['ffconcat version 1.0']
for file,seconds in segments:
    lines += [f"file 'frames/{file}'",'option framerate 30',f'duration {seconds:.9f}']
lines += ["file 'frames/credits.png'",'option framerate 30']
(ROOT/'frames.ffconcat').write_text('\n'.join(lines)+'\n',encoding='utf-8')
DIST.mkdir(exist_ok=True)
output=DIST/'Hindi-Sounds.mp4'
subprocess.run([FFMPEG,'-y','-hide_banner','-loglevel','warning','-safe','0','-f','concat','-i',str(ROOT/'frames.ffconcat'),'-i',str(ROOT/'soundtrack.wav'),'-map','0:v:0','-map','1:a:0','-t',f'{clock/FPS:.9f}','-r',str(FPS),'-c:v','libx264','-preset','medium','-crf','23','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart','-metadata','title=Hindi Sounds - Letters and sounds','-metadata','comment=Pronunciation audio: Mansi Bajaj, Hindi at the University of Texas at Austin. CC BY 4.0. https://hindi.la.utexas.edu/resources/pronouncing-the-hindi-alphabet/ | Audio excerpts trimmed and normalized.',str(output)],check=True,cwd=ROOT)
report={'output':output.name,'duration':clock/FPS,'count':len(items),'sizeBytes':output.stat().st_size,'frameRate':FPS,'dimensions':[1920,1080],'timeline':timeline}
(ROOT/'video-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='timeline'},ensure_ascii=False))
