/* Real Next rendering of every exported snapshot; API traffic stays in this
 * isolated browser context. Never creates users or attempts in the live DB. */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require('../frontend/node_modules/@playwright/test');
const root = path.resolve(__dirname, '..');
const args = process.argv.slice(2);
const arg = (name, fallback) => args.includes(name) ? args[args.indexOf(name) + 1] : fallback;
const input = path.resolve(arg('--input', 'tmp/acervo-validacao/2026-11-03-inicial'));
const url = arg('--url', 'http://127.0.0.1:3100');
const workers = Number(arg('--workers', '4'));
const maxExams = Number(arg('--max-exams', '10000'));
const screenshots = !args.includes('--no-screenshots');
const captureIssues=args.includes('--capture-issues');
const read = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const sha = value => crypto.createHash('sha256').update(value).digest('hex');
const write = (file, data) => {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file + '.tmp', JSON.stringify(data, null, 2) + '\n');
  fs.renameSync(file + '.tmp', file);
};
if (!input.startsWith(root + '/tmp/')) throw Error('A saída deve ficar em tmp/ do projeto.');
const manifest = read(path.join(input, 'manifest.json'));
const build = fs.readFileSync(path.join(root, 'frontend/.next/BUILD_ID'), 'utf8').trim();
const harness=sha(fs.readFileSync(__filename));
const compatibleFile=arg('--compatible-harness',null);
let compatibleHarness=null;
if(compatibleFile){
  const old=fs.readFileSync(compatibleFile,'utf8'),current=fs.readFileSync(__filename,'utf8');
  const inspection=s=>s.slice(s.lastIndexOf('async function inspect('),s.lastIndexOf('async function main('));
  if(inspection(old)!==inspection(current))throw Error('A implementação das verificações visuais mudou; não reutilize esse auditor.');
  compatibleHarness=sha(Buffer.from(old));
}
const jobs = [];
for (const exam of manifest.index.slice(0, maxExams)) {
  for (const [viewport, size] of Object.entries({ desktop: {width:1440,height:1080}, mobile: {width:390,height:844} })) {
    jobs.push({exam, viewport, size});
  }
}
async function inspect(page, item, official) {
  return page.evaluate(({item, official}) => {
    const panel = document.querySelector('.question-panel');
    const issues = [];
    const add = (code, detail) => issues.push({code, detail});
    const letters = [...panel.querySelectorAll('.alternative-letter')].map(e => e.textContent);
    if (letters.join('') !== 'ABCDE') add('alternative_order', letters);
    const right = [...panel.querySelectorAll('.alternative.right .alternative-letter')].map(e => e.textContent);
    if (right.join('') !== (official || '')) add('visible_answer_key', {right, official});
    if (panel.querySelectorAll('.katex-error').length) add('latex_error', panel.querySelector('.katex-error').textContent);
    const imgs = [...panel.querySelectorAll('img')].map(img => ({src:img.getAttribute('src'), loaded:img.complete && img.naturalWidth>0, width:img.clientWidth, height:img.clientHeight, naturalWidth:img.naturalWidth, naturalHeight:img.naturalHeight}));
    for (const img of imgs) if (!img.loaded || !img.width || !img.height) add('image_not_rendered', img);
    if (document.documentElement.scrollWidth > innerWidth + 2) add('viewport_overflow', {width:innerWidth, content:document.documentElement.scrollWidth});
    for (const el of panel.querySelectorAll('.alternative-text, .native-paragraph, .figure-caption')) {
      if (el.scrollWidth > el.clientWidth + 3 && !el.querySelector('.math-inline')) add('text_overflow', el.textContent.slice(0,160));
    }
    const expectedImages = item.images.length + item.alternatives.filter(a=>a.image).length + (item.blocks||[]).filter(b=>b.type==='image').length;
    // Blocks supersede the legacy image list. Count actual native image blocks.
    const wanted = (item.blocks||[]).length ? (item.blocks||[]).filter(b=>b.type==='image').length + item.alternatives.filter(a=>a.image).length : expectedImages;
    if (imgs.length !== wanted) add('image_cardinality', {actual:imgs.length, expected:wanted});
    const pending = [...panel.querySelectorAll('.notice-box')].some(e=>e.textContent.includes('pendências de apresentação'));
    if (pending !== !!item.preparation_errors) add('missing_preparation_notice', item.preparation_errors);
    if (item.annulled !== [...panel.querySelectorAll('.notice-box')].some(e=>e.textContent.includes('Questão anulada'))) add('annulment_notice', item.annulled);
    return {issues, images:imgs, tables:panel.querySelectorAll('table').length, formulas:panel.querySelectorAll('.katex').length, height:panel.scrollHeight, width:panel.clientWidth};
  }, {item, official});
}
async function main() {
  const started=Date.now();
  const browser = await chromium.launch({headless:true, executablePath:arg('--chrome','/usr/bin/google-chrome'), args:['--disable-dev-shm-usage']});
  let completed=0;
  const results=[];
  async function worker() {
    while (jobs.length) {
      const {exam,viewport,size} = jobs.shift();
      const target = path.join(input,'browser',viewport,exam.id+'.json');
      const run = read(path.join(input,exam.run_file));
      const sources = read(path.join(input,exam.source_report));
      const previous = fs.existsSync(target) ? read(target) : {items:[]};
      const fingerprint=(item,source,h,withAssets=true)=>sha(JSON.stringify([build,h,captureIssues,item,source.official_answer,size,
        ...(withAssets?[sources.source_sha256,sources.answer_key_sha256,sources.assets]:[])]));
      const reusable=(item,i)=>{
        const source=sources.items.find(q=>q.number===item.number);
        const old=previous.items.find(q=>q.number===item.number && (q.fingerprint===fingerprint(item,source,harness)
          || compatibleHarness && q.fingerprint===fingerprint(item,source,compatibleHarness,false)));
        return old && old.complete && (!screenshots || captureIssues && !item.preparation_errors && !old.light.issues.length && !old.dark.issues.length && i>0
          || old.screenshot && fs.existsSync(path.join(input,old.screenshot))) ? old : null;
      };
      if(previous.complete && !previous.errors.length && run.items.every((item,i)=>reusable(item,i))){
        results.push(previous);completed++;console.log(`${completed}/${manifest.index.slice(0,maxExams).length*2}: ${exam.id} ${viewport} (cache validado)`);continue;
      }
      const context = await browser.newContext({viewport:size, colorScheme:'light', reducedMotion:'reduce'});
      const errors=[];
      await context.route('**/api/**', async route => {
        const req=route.request(); const u=new URL(req.url());
        if (req.method()!=='GET') throw Error('A auditoria não permite gravações: '+req.url());
        if (u.pathname==='/api/me') return route.fulfill({json:{id:'audit',name:'Conferência do acervo',email:'audit@invalid.local',role:'student'}});
        if (u.pathname==='/api/exam-runs/'+run.id) return route.fulfill({json:run});
        if (u.pathname.startsWith('/api/assets/')) {
          const asset=path.resolve(root,'data',decodeURIComponent(u.pathname.slice(5)).replace(/^\/+/,''));
          if (!asset.startsWith(root+'/data/assets/')) throw Error('Asset fora da raiz.');
          return route.fulfill({path:asset});
        }
        return route.fulfill({status:404,json:{detail:'Rota não prevista na auditoria: '+u.pathname}});
      });
      const page=await context.newPage();
      const cdp=await context.newCDPSession(page);
      page.on('pageerror', error=>errors.push(String(error)));
      const items=[];
      try {
        await page.goto(url+'/runs/'+run.id,{waitUntil:'domcontentloaded'});
        await page.locator('.question-panel h2').waitFor();
        await page.evaluate(()=>document.fonts.ready);
        for (let i=0;i<run.items.length;i++) {
          const questionStarted=Date.now();
          const item=run.items[i]; const source=sources.items.find(q=>q.number===item.number);
          const currentFingerprint=fingerprint(item,source,harness);
          const old=reusable(item,i);
          if (i>0) {
            await page.locator('.question-navigation button').last().evaluate(button=>button.click());
          }
          await page.waitForFunction(n=>document.querySelector('.question-panel h2')?.textContent===`Questão ${String(n).padStart(2,'0')}`, item.number,{polling:10});
          if (old) { items.push(old); continue; }
          await page.locator('.question-panel img').evaluateAll(imgs=>Promise.all(imgs.map(img=>img.complete?null:new Promise(resolve=>{
            img.addEventListener('load',resolve,{once:true});img.addEventListener('error',resolve,{once:true});
          }))));
          await page.evaluate(()=>document.fonts.status==='loading'?document.fonts.ready:null);
          const light=await inspect(page,item,source.official_answer);
          await page.evaluate(()=>document.documentElement.dataset.theme='dark');
          const dark=await inspect(page,item,source.official_answer);
          await page.evaluate(()=>document.documentElement.dataset.theme='light');
          const record={id:item.id,number:item.number,fingerprint:currentFingerprint,complete:true,light,dark};
          if (screenshots && (!captureIssues || item.preparation_errors || light.issues.length || dark.issues.length || i===0)) {
            await page.locator('.question-panel img').evaluateAll(imgs=>Promise.all(imgs.map(img=>img.decode().catch(()=>{}))));
            const file=path.join('screenshots',viewport,exam.id,`${item.number}-${currentFingerprint.slice(0,12)}.jpg`);
            fs.mkdirSync(path.dirname(path.join(input,file)),{recursive:true});
            await page.evaluate(()=>document.fonts.status==='loading'?document.fonts.ready:null);
            const clip=await page.locator('.question-panel').evaluate(panel=>{const r=panel.getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height,scale:1};});
            const shot=await cdp.send('Page.captureScreenshot',{format:'jpeg',quality:65,clip,captureBeyondViewport:true,fromSurface:true,optimizeForSpeed:true});
            fs.writeFileSync(path.join(input,file),Buffer.from(shot.data,'base64'));
            record.screenshot=file;
          }
          record.elapsed_ms=Date.now()-questionStarted;
          items.push(record);
          if (i%10===0) write(target,{exam:exam.id,viewport,size,build,complete:false,items,errors});
          if ((i+1)%30===0) console.log(`${exam.id} ${viewport}: ${i+1}/${run.items.length} questões.`);
        }
        const report={exam:exam.id,viewport,size,build,harness,complete:true,items,errors};
        write(target,report); results.push(report);
      } catch (error) {
        const report={exam:exam.id,viewport,size,build,complete:false,items,errors:[...errors,String(error)]};
        write(target,report); results.push(report);
      } finally { await context.close(); }
      completed++;
      console.log(`${completed}/${manifest.index.slice(0,maxExams).length*2}: ${exam.id} ${viewport} (${items.length}/${run.items.length})`);
    }
  }
  try {await Promise.all(Array.from({length:workers},worker));} finally {await browser.close();}
  const findings={};
  for(const r of results) for(const q of r.items) for(const theme of ['light','dark']) for(const issue of q[theme].issues) findings[issue.code]=(findings[issue.code]||0)+1;
  const report={build,harness,compatible_harness_sha256:compatibleHarness,exams:manifest.index.slice(0,maxExams).length,viewports:results.length,questions:results.reduce((s,r)=>s+r.items.length,0),complete:results.every(r=>r.complete),errors:results.flatMap(r=>r.errors.map(message=>({exam:r.exam,viewport:r.viewport,message}))),findings,screenshots:results.reduce((s,r)=>s+r.items.filter(q=>q.screenshot).length,0),capture_policy:screenshots?(captureIssues?'issues_and_first_question':'every_question'):'none',elapsed_seconds:(Date.now()-started)/1000,manual_visual_review_complete:false};
  write(path.join(input,'browser-report.json'),report);console.log(JSON.stringify(report));
  if(!report.complete||report.errors.length) process.exitCode=1;
}
main().catch(error=>{console.error(error);process.exitCode=1;});
