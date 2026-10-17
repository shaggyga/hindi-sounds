// Render the video artwork in Chromium so complex Devanagari is shaped correctly.
// This runs headlessly; it does not control an interactive application.
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const root = __dirname;
const checkOnly = process.argv.includes('--check');
const data = checkOnly ? null : JSON.parse(fs.readFileSync(path.join(root, 'video-data.json'), 'utf8'));
const out = path.join(root, 'frames');
if (!checkOnly) fs.mkdirSync(out, {recursive:true});

const html = `<!doctype html><html><meta charset="utf-8"><style>
* { box-sizing:border-box; }
html,body { margin:0;width:1920px;height:1080px;overflow:hidden; }
body { background:#10141c;color:#f4f7fb;font-family:'Segoe UI',Arial,sans-serif; }
.page { position:relative;width:100%;height:100%;padding:66px 94px; }
.top { display:flex;align-items:center;justify-content:space-between;height:48px; }
.brand { font-size:28px;font-weight:600;letter-spacing:.2px; }
.counter { font-size:24px;color:#8c99ad;font-variant-numeric:tabular-nums; }
.current { color:#f4f7fb; }
.stage { height:818px;display:flex;align-items:center;justify-content:center;position:relative; }
.card { width:1390px;height:714px;background:#171d28;border:2px solid #252e3d;border-radius:28px;display:flex;align-items:center;justify-content:center; }
.card.active { background:#192330;border-color:#8ec5ff;box-shadow:0 0 60px #8ec5ff08; }
.glyph { font-family:'Nirmala UI';font-size:440px;line-height:1.35;font-weight:400;margin-top:-46px; }
.active .glyph {color:#8ec5ff;}
.footer {position:absolute;left:94px;right:94px;bottom:70px;display:flex;justify-content:space-between;align-items:center;color:#8c99ad;font-size:22px;}
.progress {position:absolute;left:94px;right:94px;bottom:40px;height:3px;background:#252e3d;}
.progress-fill {height:3px;background:#8ec5ff;}
.intro {text-align:center;max-width:1450px;}
.intro .symbol {font-family:'Nirmala UI';font-size:250px;color:#8ec5ff;line-height:1.35;margin-top:-44px;}
.intro h1 {font-size:72px;font-weight:500;letter-spacing:-1.2px;margin:6px 0 26px;}
.intro p {font-size:29px;line-height:1.6;color:#8c99ad;margin:0;}
.intro .meta {font-size:21px;letter-spacing:.5px;margin-top:35px;}
.credits {max-width:1530px;}
.credits h1 {font-size:60px;font-weight:500;margin:0 0 48px;}
.credits p {font-size:28px;line-height:1.75;color:#a8b3c4;margin:13px 0;}
.credits .url {font-size:25px;color:#8ec5ff;}
</style><div class="page"><div class="top"><div class="brand">Hindi Sounds</div><div class="counter" id="counter"></div></div><div class="stage" id="stage"></div><div class="footer"><span id="category"></span><span id="round"></span></div><div class="progress"><div class="progress-fill" id="progress"></div></div></div></html>`;

(async()=>{
  const launchOptions = {headless:true};
  if (process.env.HINDI_SOUNDS_BROWSER_PATH) launchOptions.executablePath = process.env.HINDI_SOUNDS_BROWSER_PATH;
  const browser = await chromium.launch(launchOptions);
  const page = await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:1});
  await page.setContent(html);
  await page.evaluate(()=>document.fonts.ready);
  if (checkOnly) {
    await page.evaluate(()=>{
      document.querySelector('#stage').innerHTML='<div class="card active"><div class="glyph">अ</div></div>';
    });
    // Render in memory so this check exercises text layout without changing artifacts.
    const rendered = await page.screenshot();
    if (!rendered.length) throw new Error('The renderer produced an empty image.');
    await browser.close();
    console.log('Chromium rendering check passed; no output files were changed.');
    return;
  }
  const set = async (stage, category, count, progress, round, file) => {
    await page.evaluate(({stage,category,count,progress,round})=>{
      document.querySelector('#stage').innerHTML=stage;
      document.querySelector('#category').textContent=category;
      document.querySelector('#counter').innerHTML=count;
      document.querySelector('#progress').style.width=progress+'%';
      document.querySelector('#round').textContent=round;
    },{stage,category,count,progress,round});
    await page.screenshot({path:path.join(out,file)});
  };
  await set(`<div class="intro"><div class="symbol">अ</div><h1>Hindi Sounds</h1><p>Watch the letter light up. Listen and repeat.</p><p class="meta">${data.items.length} letters & signs · One complete round</p></div>`,'Letters & sounds','',0,'', 'intro.png');
  for(let i=0;i<data.items.length;i++) {
    const item=data.items[i];
    for(const active of [false,true]) {
      await set(`<div class="card ${active?'active':''}"><div class="glyph">${item.letter}</div></div>`,item.category,`<span class="current">${String(i+1).padStart(2,'0')}</span> / ${data.items.length}`,(i+1)/data.items.length*100,'Round 1',`${String(i).padStart(2,'0')}-${active?'active':'idle'}.png`);
    }
  }
  await set('<div class="intro"><h1>Round complete</h1><p>Replay to practice the sounds again.</p></div>','Letters & sounds',`${data.items.length} / ${data.items.length}`,100,'Round 1','outro.png');
  await set(`<div class="credits"><h1>Audio credits</h1><p>${data.attribution.credit}</p><p>${data.attribution.adaptation}</p><p class="url">${data.attribution.url}</p><p>${data.attribution.license}</p><p class="url">creativecommons.org/licenses/by/4.0/</p></div>`,'Letters & sounds','',100,'','credits.png');
  await browser.close();
  console.log(`Rendered ${data.items.length*2+3} frames with Chromium / Nirmala UI shaping.`);
})().catch(e=>{console.error(e);process.exit(1)});
