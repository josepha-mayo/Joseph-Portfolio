const { chromium, expect } = require('@playwright/test');
const fs = require('node:fs/promises');
const crypto = require('node:crypto');
const { spawn } = require('node:child_process');
const path = require('node:path');
const base = process.env.CV_TEST_ORIGIN || 'http://127.0.0.1:3100';
const out = path.resolve(process.env.CV_TEST_OUT || '/tmp/cv-verification');
const sha = b => crypto.createHash('sha256').update(b).digest('hex');
const pause = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  await fs.mkdir(out, {recursive:true});
  const expected = sha(await fs.readFile('public/Joseph_Ayanda_CV.pdf'));
  const server = process.env.CV_TEST_ORIGIN ? null : spawn('npm',['run','start','--','--hostname','127.0.0.1','--port','3100'],{stdio:'ignore'});
  let browser;
  try {
    let ready=false;
    for(let i=0;i<90;i++) { try {const r=await fetch(base);if(r.ok){ready=true;break;}}catch{} await pause(1000); }
    if(!ready) throw new Error('Portfolio server not ready');
    browser=await chromium.launch({headless:true});
    const results=[];
    for(const [label,viewport] of [['desktop',{width:1440,height:1000}],['mobile',{width:390,height:844}]]) {
      const context=await browser.newContext({viewport,acceptDownloads:true});
      const page=await context.newPage(); const errors=[];
      page.on('pageerror',e=>errors.push(e.message));
      await page.goto(base,{waitUntil:'domcontentloaded'});
      await expect(page.locator('h1')).toHaveText('ai/ml engineer');
      const button=page.locator('header a[href="/Joseph_Ayanda_CV.pdf"]');
      await expect(button).toBeVisible();
      await expect(button).toHaveAttribute('download','Joseph_Ayanda_CV.pdf');
      await expect(button).toHaveAttribute('aria-label','Download CV (PDF, 3 pages)');
      const response=await context.request.get(base+'/Joseph_Ayanda_CV.pdf');
      if(response.status()!==200 || !response.headers()['content-type'].includes('application/pdf')) throw new Error('Not a public PDF response');
      const data=await response.body(); if(sha(data)!==expected) throw new Error('HTTP PDF bytes changed');
      const pending=page.waitForEvent('download');await button.click();const download=await pending;
      const target=path.join(out,label+'-download.pdf');await download.saveAs(target);
      if(sha(await fs.readFile(target))!==expected || download.suggestedFilename()!=='Joseph_Ayanda_CV.pdf') throw new Error('Browser download mismatch');
      const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+1);
      if(overflow) throw new Error(label+' horizontal overflow');
      await expect(page.locator('body')).toContainText('DOOMFLY');
      await expect(page.locator('body')).toContainText('DR-OPIC');
      await page.screenshot({path:path.join(out,label+'.png')});
      if(errors.length) throw new Error('Uncaught browser errors: '+errors.join('; '));
      results.push({viewport:label,status:'passed',http_status:200,download_sha256:expected,download_bytes:data.length,horizontal_overflow:false});
      await context.close();
    }
    await fs.writeFile(path.join(out,'VERIFICATION.json'),JSON.stringify({status:'passed',origin:base,expected_pdf_sha256:expected,results},null,2));
    console.log(JSON.stringify({status:'passed',results}));
  } finally {if(browser) await browser.close();if(server)server.kill('SIGTERM');}
})().catch(e=>{console.error(e);process.exitCode=1;});
