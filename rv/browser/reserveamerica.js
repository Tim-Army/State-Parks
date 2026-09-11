// ReserveAmerica per-site scraper (NY, TX, GA, OR, IA, UT, NE, NM, NC, MT, DE, MD).
// Run in a tab on <state>.reserveamerica.com:
//   await RA.start('NY')      RA.st2() -> progress      RA.agg() -> {n, h, text} for rv/sites/<st>.txt
// Park list: campgroundDirectoryList.do (paged by 25). Sites: campsitePaging.do (paged by 25). The pager repeats its
// last page instead of returning empty, so stop when a page adds no new site id. The "Equip length / Driveway" cell
// gives length and back-in/pull-through; the amenity icons' alt text gives electric amps / water / full hookup.
// The max-people cell can contain an ADA icon, so the length cell is found relative to it, not by column position.
// agg(): header lines T| (site types), E| (driveway kinds), A| (amenity strings); then Park|len:type:entry:amen:count
// SLEEP races a Web Worker timer (not throttled in background tabs) against a plain timer (in case the page's
// CSP blocks blob: workers, as reserve.alapark.com does); whichever fires first wins.
{
  const P = {}; let c = 0, w = null;
  try {
    w = new Worker(URL.createObjectURL(new Blob(['onmessage=e=>setTimeout(()=>postMessage(e.data[0]),e.data[1])'], { type: 'text/javascript' })));
    w.onmessage = e => { if (P[e.data]) { P[e.data](); delete P[e.data]; } };
  } catch (e) { w = null; }
  window.SLEEP = ms => new Promise(r => {
    const id = ++c; P[id] = r;
    if (w) w.postMessage([id, ms]);
    setTimeout(() => { if (P[id]) { P[id](); delete P[id]; } }, ms + 250);
  });
}
window.RA = {
  async start(cc, gap = 400) {
    this.cc = cc; this.gap = gap; const k = 'ra_' + cc, ls = s => JSON.parse(localStorage.getItem(k + s) || 'null');
    this.parks = ls('_p'); this.sites = ls('_s') || {};
    if (!this.parks || !Object.keys(this.parks).length) {
      this.parks = {};
      for (let s = 0; s < 2000; s += 25) {
        const h = await (await fetch(`/campgroundDirectoryList.do?contractCode=${cc}&startIdx=${s}`)).text(), b = Object.keys(this.parks).length;
        for (const m of h.matchAll(/parkId=(\d+)'[^>]*>\s*([^<]+?)\s*</g))
          if (!/Enter Date/i.test(m[2])) this.parks[m[1]] = m[2];
        if (Object.keys(this.parks).length === b) break;
      }
    }
    this.save(); this.gen = (this.gen || 0) + 1; this.loop2(this.gen); return this.st2();
  },
  save() { const k = 'ra_' + this.cc; localStorage.setItem(k + '_p', JSON.stringify(this.parks)); localStorage.setItem(k + '_s', JSON.stringify(this.sites)); },
  parse(h) {
    const o = [], c = h.split(/<div id='div(\d+)' class='siteListLabel'>/);
    for (let k = 1; k < c.length; k += 2) {
      const t = c[k + 1] || '';
      const cells = [...t.matchAll(/<div class='td[^']*'>([\s\S]*?)<\/div>/g)].map(m => m[1]);
      const m = t.match(/<div class='td maxPeopleCell'>[\s\S]*?<\/div>\s*<div class='td'>\s*(\d+)?\s*([^<]*)<\/div>/);
      const am = t.split('amenitiesicons')[1] || '';
      const alts = [...am.split('sitescompare')[0].matchAll(/alt='([^']+)'/g)].map(x => x[1]).filter(a => /hookup|amp|water|sewer/i.test(a) && !/- no$/i.test(a));
      o.push([c[k], m && m[1] ? +m[1] : 0, (m && m[2] || '').trim(), (cells[1] || '').replace(/<[^>]+>/g, '').trim(), alts.join('+')]);
    }
    return o;
  },
  async page(pid, s) {
    for (let t = 0, w = 20000; t < 9; t++, w = Math.min(w * 2, 300000)) {
      try { const r = await fetch(`/campsitePaging.do?contractCode=${this.cc}&parkId=${pid}&startIdx=${s}`); if (r.ok) return await r.text(); this.last = r.status; } catch (e) { this.last = 'err'; }
      this.waiting = w; await SLEEP(w); this.waiting = 0;
    }
    return '';
  },
  async loop2(g) {
    for (const pid of Object.keys(this.parks)) {
      if (this.gen !== g) return;
      if (this.sites[pid]) continue;
      this.cur = pid; const seen = {};
      for (let s = 0; s < 3000; s += 25) {
        const r = this.parse(await this.page(pid, s)); let a = 0;
        for (const [id, l, e, ty, am] of r) if (!seen[id]) { seen[id] = [l, e, ty, am]; a++; }
        await SLEEP(this.gap);
        if (r.length < 25 || a === 0) break;
      }
      if (this.gen !== g) return;
      this.sites[pid] = Object.values(seen); this.save();
    }
    this.finished = true;
  },
  st2() { return { cc: this.cc, done: Object.keys(this.sites).length, of: Object.keys(this.parks).length, sites: Object.values(this.sites).reduce((a, b) => a + b.length, 0), waiting: this.waiting, last: this.last, finished: !!this.finished }; },
  agg() {
    const D = { T: [], E: [], A: [] }, ix = (d, v) => { let i = D[d].indexOf(v); if (i < 0) { i = D[d].length; D[d].push(v); } return i; };
    const lines = []; let n = 0, h = 0;
    for (const [pid, S] of Object.entries(this.sites)) {
      const c = {};
      for (const [l, e, ty, am] of S) { if (!(l > 0)) continue; const k = [l, ix('T', ty), ix('E', e), ix('A', am)].join(':'); c[k] = (c[k] || 0) + 1; }
      const ks = Object.entries(c); if (!ks.length) continue;
      for (const [k, v] of ks) { n += v; h = (h + k.split(':').reduce((a, b) => a * 31 + +b, 7) * v) % 1e9; }
      lines.push(this.parks[pid].replace(/[|\n]/g, ' ') + '|' + ks.map(([k, v]) => k + ':' + v).join(','));
    }
    return { n, h, text: ['T|' + D.T.join('~'), 'E|' + D.E.join('~'), 'A|' + D.A.join('~'), ...lines].join('\n') };
  }
};
