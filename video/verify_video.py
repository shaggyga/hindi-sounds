from pathlib import Path
import json, subprocess, re, wave
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'assets'
report=json.loads((ROOT/'video-report.json').read_text(encoding='utf-8'))
ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
output=str(ROOT/'Hindi-Sounds.mp4')
probe=subprocess.run([ffmpeg,'-hide_banner','-i',output],capture_output=True,text=True)
(ROOT/'encoded-metadata.txt').write_text(probe.stderr,encoding='utf-8')
subprocess.run([ffmpeg,'-v','error','-i',output,'-f','null','-'],check=True)
frames=[round(x['audioStart']*30)+3 for x in report['timeline']]
select='+'.join(f'eq(n\\,{f})' for f in frames)
(ROOT/'verified-frames').mkdir(exist_ok=True)
subprocess.run([ffmpeg,'-y','-v','error','-i',output,'-vf','select='+select,'-fps_mode','vfr',str(ROOT/'verified-frames'/'%02d.png')],check=True)
errors=[]
for i,item in enumerate(report['timeline']):
    expected=np.array(Image.open(ROOT/'frames'/f'{i:02d}-active.png').convert('RGB'),dtype=np.int16)
    actual=np.array(Image.open(ROOT/'verified-frames'/f'{i+1:02d}.png').convert('RGB'),dtype=np.int16)
    mae=float(np.abs(expected-actual).mean())
    errors.append(mae)
    assert mae<3, (i,mae)
subprocess.run([ffmpeg,'-y','-v','error','-i',output,'-vn','-ac','1','-ar','44100',str(ROOT/'decoded-audio.wav')],check=True)
with wave.open(str(ROOT/'decoded-audio.wav'),'rb') as f:
    decoded=np.frombuffer(f.readframes(f.getnframes()),dtype=np.int16).astype(float)
correlations=[]
for x in report['timeline']:
    with wave.open(str(SOURCE/x['source']),'rb') as f:
        source=np.frombuffer(f.readframes(f.getnframes()),dtype=np.int16).astype(float)
    start=round(x['audioStart']*44100)
    actual=decoded[start:start+len(source)]
    correlation=float(np.corrcoef(actual,source)[0,1])
    correlations.append(correlation)
    assert correlation>.97, (x['id'],correlation)

# Contact sheet of the actual encoded video at each pronunciation.
thumb_w,thumb_h=384,216
sheet=Image.new('RGB',(thumb_w*6,thumb_h*8),(16,20,28))
for i in range(report['count']):
    im=Image.open(ROOT/'verified-frames'/f'{i+1:02d}.png').convert('RGB')
    im.thumbnail((thumb_w,thumb_h))
    sheet.paste(im,((i%6)*thumb_w,(i//6)*thumb_h))
sheet.save(ROOT/'video-contact-sheet.jpg',quality=92)
result={'decoded_without_errors':True,'verified_items':len(errors),'maximum_frame_mean_absolute_error':max(errors),'minimum_audio_correlation':min(correlations),'decoded_audio_seconds':len(decoded)/44100,'intended_duration_seconds':report['duration'],'largest_highlight_tail_seconds':max(x['highlightEnd']-x['audioEnd'] for x in report['timeline'])}
(ROOT/'validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
