// Re-scrape state-park campsites with a real (headless) browser, using the same in-page scrapers in rv/browser/.
//   npm install playwright && npx playwright install chromium
//   node rv/refresh_states.mjs              # every state
//   node rv/refresh_states.mjs ny tx wa     # just these
// Writes rv/sites/<st>.txt for each state that finishes and passes its checksum; a state that fails keeps its old file.
// Then run: python3 rv/build_sites.py && python3 build_site.py
import { chromium } from 'playwright';
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const JS = f => readFileSync(join(HERE, 'browser', f), 'utf8');
const RA = (host, cc) => ({ kind: 'ra', url: `https://${host}.reserveamerica.com/`, cc });
const UDx = (url, base, extra = {}) => ({ kind: 'ud', url, base, ...extra });
const STATES = {
  ca: UDx('https://www.reservecalifornia.com/', null),
  fl: UDx('https://floridardr.usedirect.com/FloridaRDR/', '/FloridaRDR/rdr/'),
  oh: UDx('https://ohiordr.usedirect.com/OhioRDR/', '/OhioRDR/rdr/', { ohioFilter: true }),
  az: UDx('https://azrdr.usedirect.com/AzRDR/', '/AzRDR/rdr/'),
  nv: UDx('https://nevadardr.usedirect.com/NevadaRDR/', '/NevadaRDR/rdr/'),
  mo: UDx('https://icampmo1.usedirect.com/', null),
  nd: UDx('https://reservendparks.com/', null),
  va: UDx('https://reservevaparks.com/', null),
  il: UDx('https://il-rdr.recreation-management.tylerapp.com/IllinoisRDR/rdr/fd/places', '/IllinoisRDR/rdr/'),
  ny: RA('newyorkstateparks', 'NY'), tx: RA('texasstateparks', 'TX'), ga: RA('gastateparks', 'GA'),
  or: RA('oregonstateparks', 'OR'), ia: RA('iowastateparks', 'IA'), ut: RA('utahstateparks', 'UT'),
  ne: RA('nebraskastateparks', 'NE'), nm: RA('newmexicostateparks', 'NM'), nc: RA('northcarolinastateparks', 'NC'),
  mt: RA('montanastateparks', 'MT'), de: RA('delawarestateparks', 'DE'), md: { kind: 'ra', url: 'https://parkreservations.maryland.gov/', cc: 'MD' },
  wa: { kind: 'gtc', url: 'https://washington.goingtocamp.com/', tenant: 'wa' },
  wi: { kind: 'gtc', url: 'https://wisconsin.goingtocamp.com/', tenant: 'wi' },
  mi: { kind: 'gtc', url: 'https://midnrreservations.com/', tenant: 'mi' },
  ky: RA('kentuckystateparks', 'KY'), in: RA('indianastateparks', 'IN'), pa: RA('pennsylvaniastateparks', 'PA'),
  ok: RA('okstateparks', 'OK'), ct: RA('connecticutstateparks', 'CT'), nh: RA('newhampshirestateparks', 'NH'),
  ri: RA('rhodeislandstateparks', 'RI'), ma: RA('massdcrcamping', 'MA'), ak: RA('alaskastateparks', 'AK'),
  vt: { kind: 'ra', url: 'https://vtstateparks-visit.com/', cc: 'VT' },
  mn: UDx('https://reservemn.usedirect.com/MinnesotaWeb/', 'https://mnrdr.usedirect.com/minnesotardr/rdr/'),
  co: { kind: 'as', url: 'https://www.cpwshop.com/camping.page', range: [50000, 50140] },
  ks: { kind: 'as', url: 'https://www.campitks.gov/camping.page', range: [519100, 519175] },
  wy: { kind: 'wy', url: 'https://reserve.wyoming.gov/web/' },
  // Tennessee, South Carolina and Arkansas (Itinio) and South Dakota and Louisiana (Brandt) answer plain HTTP:
  // see rv/scrape_itinio.py and rv/scrape_brandt.py, which the workflow runs separately.
};
const FILE = { ud: 'usedirect.js', ra: 'reserveamerica.js', gtc: 'goingtocamp.js', as: 'aspira.js', wy: 'wyoming.js' };
const OBJ = { ud: 'UD', ra: 'RA', gtc: 'GTC', as: 'AS', wy: 'WY' };

function checksum(text) {
  let n = 0, h = 0;
  for (const line of text.split('\n')) {
    if ((line[1] === '|' && 'TEACSMH'.includes(line[0])) || !line.includes('|')) continue;
    for (const x of line.slice(line.indexOf('|') + 1).split(',')) {
      const a = x.split(':').map(Number), v = a.pop();
      n += v; h = (h + a.reduce((r, b) => r * 31 + b, 7) * v) % 1e9;
    }
  }
  return { n, h };
}

async function run(ctx, st, cfg) {
  const page = await ctx.newPage();
  const log = (...a) => console.log(new Date().toISOString().slice(11, 19), st, ...a);
  try {
    let started;
    for (let attempt = 1; attempt <= 3; attempt++) {                 // an empty park list is usually a transient block: reload and retry
    await page.goto(cfg.url, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await page.waitForTimeout(3000 * attempt);
    await page.addScriptTag({ content: JS(FILE[cfg.kind]) });
    started = await page.evaluate(async cfg => {
      if (cfg.kind === 'ud') {
        let B = cfg.base || globalThis.apiurl;
        if (!B) { try { B = (await (await fetch('/config.json')).json()).rdrApiUrl; } catch (e) {} }
        return UD.start(cfg.st, B, { ohioFilter: !!cfg.ohioFilter });
      }
      if (cfg.kind === 'ra') return RA.start(cfg.cc);
      if (cfg.kind === 'as') return AS.start(cfg.st, cfg.range[0], cfg.range[1]);
      if (cfg.kind === 'wy') { await WY.init(); WY.run(); return WY.st(); }
      return GTC.start(cfg.tenant, GTC.TENANTS[cfg.tenant]);
    }, { ...cfg, st });
    if (started && started.of === 0 && cfg.kind !== 'as') { log('empty start, retrying', attempt); await page.waitForTimeout(30000); continue; }
    break;
    }
    log('started', JSON.stringify(started));
    for (let i = 0; ; i++) {
      await page.waitForTimeout(30000);
      const s = await page.evaluate(o => (window[o].st2 || window[o].st).call(window[o]), OBJ[cfg.kind]);
      if (i % 10 === 0 || s.finished) log(JSON.stringify(s));
      if (s.finished) break;
    }
    const a = await page.evaluate(o => window[o].agg(), OBJ[cfg.kind]);
    const c = checksum(a.text);
    if (c.n !== a.n || c.h !== a.h || a.n === 0) throw new Error(`checksum mismatch or empty: page ${a.n}/${a.h} file ${c.n}/${c.h}`);
    writeFileSync(join(HERE, 'sites', st + '.txt'), a.text);
    log('wrote', a.n, 'sites');
    return [st, a.n];
  } catch (e) {
    log('FAILED', e.message);
    return [st, null];
  } finally {
    await page.close();
  }
}

const want = process.argv.slice(2).length ? process.argv.slice(2) : Object.keys(STATES);
const browser = await chromium.launch({ args: ['--disable-background-timer-throttling', '--disable-renderer-backgrounding'] });
const ctx = await browser.newContext({ userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36' });
const results = await Promise.all(want.map(st => run(ctx, st, STATES[st])));
await browser.close();
console.log(JSON.stringify(Object.fromEntries(results)));
if (results.every(([, n]) => n === null)) process.exit(1);
