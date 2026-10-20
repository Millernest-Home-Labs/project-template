// convert-pipeline.js <input.png> <output.svg>
// Runs the 3-stage logo pipeline: pngtosvg.com -> vecta.io/nano -> svgcrop.com
// Requires: playwright (set NODE_PATH to a node_modules containing playwright)
const { chromium } = require('playwright');
const fs = require('fs');
const os = require('os');
const path = require('path');

const input = process.argv[2];
const output = process.argv[3];
if (!input || !output) {
  console.error('usage: node convert-pipeline.js <input.png> <output.svg>');
  process.exit(1);
}

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'svgpipe-'));
const stage1Path = path.join(tmp, 'stage1.svg');
const stage2Path = path.join(tmp, 'stage2.svg');
const sizes = [];
const label = (p) => `${Math.round(fs.statSync(p).size)} B`;

function stripWhiteBackground(svg) {
  return svg
    .replace(/<path[^>]*fill="#ffffff"[^>]*\/>/g, '')
    .replace(/<rect[^>]*fill="#ffffff"[^>]*\/>/g, '');
}

async function withPage(url, fn) {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  page.setDefaultTimeout(90000);
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await fn(page);
  } finally {
    await browser.close();
  }
}

async function stage1(pngPath, outPath) {
  await withPage('https://www.pngtosvg.com/', async (page) => {
    await page.waitForTimeout(2500);
    await page.locator('input[type=file]').setInputFiles(pngPath);
    await page.locator('button:has-text("Download")').first().waitFor({ state: 'visible', timeout: 60000 });
    await page.waitForTimeout(2000);
    await page.locator('button', { hasText: 'Logo / Clip art' }).first().click();
    await page.waitForTimeout(8000);
    await page.locator('button:has-text("Download")').first().click();
    const svgOpt = page.locator('button:has-text("SVG")').first();
    await svgOpt.waitFor({ state: 'visible', timeout: 30000 });
    const dl = page.waitForEvent('download', { timeout: 60000 });
    await svgOpt.click();
    const download = await dl;
    await download.saveAs(outPath);
  });
}

async function stage2(svgPath, outPath) {
  await withPage('https://vecta.io/nano', async (page) => {
    await page.waitForTimeout(3000);
    await page.evaluate(() => {
      window.__blobTexts = [];
      const orig = URL.createObjectURL.bind(URL);
      URL.createObjectURL = function (obj) {
        try {
          if (obj instanceof Blob) obj.text().then((t) => window.__blobTexts.push({ size: obj.size, type: obj.type, text: t }));
        } catch (e) {}
        return orig(obj);
      };
    });
    const b64 = fs.readFileSync(svgPath).toString('base64');
    await page.evaluate(({ b64 }) => {
      const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
      const file = new File([bytes], 'input.svg', { type: 'image/svg+xml' });
      const dt = new DataTransfer();
      dt.items.add(file);
      const zone = document.getElementById('drop.id') || document.body;
      zone.dispatchEvent(new DragEvent('drop', { dataTransfer: dt, bubbles: true, cancelable: true }));
    }, { b64 });
    await page.waitForTimeout(15000);
    await page.evaluate(() => {
      const a = [...document.querySelectorAll('a')].find(
        (x) => (x.textContent || '').trim() === 'Download' && x.getBoundingClientRect().width > 0
      );
      if (!a) throw new Error('Vecta Download anchor not found');
      a.click();
    });
    await page.waitForTimeout(4000);
    const blobs = await page.evaluate(() => window.__blobTexts);
    const last = blobs[blobs.length - 1];
    if (!last || !/<svg/.test(last.text)) throw new Error('no compressed SVG blob captured from Vecta');
    fs.writeFileSync(outPath, last.text);
  });
}

async function stage3(svgPath, outPath) {
  await withPage('https://svgcrop.com/', async (page) => {
    await page.waitForTimeout(2000);
    await page.locator('#myfile').setInputFiles(svgPath);
    await page.waitForSelector('.ButtonWrap a[download*="-cropped"]', { timeout: 60000 });
    await page.waitForTimeout(2000);
    const href = await page.locator('.ButtonWrap a[download*="-cropped"]').first().getAttribute('href');
    const b64 = href.replace(/^data:image\/svg\+xml;base64,/, '');
    fs.writeFileSync(outPath, Buffer.from(b64, 'base64').toString('utf8'));
  });
}

(async () => {
  sizes.push(['source PNG', label(input)]);
  console.log('Stage 1: pngtosvg.com (Logo / Clip art mode)...');
  await stage1(input, stage1Path);
  let svg = fs.readFileSync(stage1Path, 'utf8');
  const before = fs.statSync(stage1Path).size;
  svg = stripWhiteBackground(svg);
  fs.writeFileSync(stage1Path, svg);
  console.log(`  traced: ${before} B -> white background removed: ${fs.statSync(stage1Path).size} B`);
  sizes.push(['stage 1 (converted, bg removed)', label(stage1Path)]);

  console.log('Stage 2: vecta.io/nano (compress)...');
  await stage2(stage1Path, stage2Path);
  sizes.push(['stage 2 (compressed)', label(stage2Path)]);

  console.log('Stage 3: svgcrop.com (crop)...');
  await stage3(stage2Path, output);
  sizes.push(['stage 3 (cropped) FINAL', label(output)]);

  console.log('\nSize table:');
  for (const [k, v] of sizes) console.log(`  ${k.padEnd(34)} ${v}`);
  fs.rmSync(tmp, { recursive: true, force: true });
})().catch((e) => {
  console.error('PIPELINE FAILED:', e.message);
  process.exit(1);
});
