// Camis / GoingToCamp per-site scraper (WA, WI, MI). Run in a tab on the tenant's booking site, then e.g.
//   await GTC.start('wa', GTC.TENANTS.wa)      GTC.st2() -> progress      GTC.agg() -> {n, h, text}
// Attribute ids are tenant-specific, so every field is resolved by its display name from /api/attribute/filterable.
// Each tenant names its fields differently (and Michigan/Wisconsin have no single "service type"), so the config
// below says which attribute holds the length, the hookups, the amps and the driveway type.
// agg(): C| categories, S| service text, M| electrical service, E| driveway kinds; then Park|len:cat:svc:amps:entry:count
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
window.GTC = {
  TENANTS: {
    wa: { len: 'Pad Length', service: 'Service Type', amps: 'Electrical Service', entry: 'Pad Location' },       // washington.goingtocamp.com
    wi: { len: 'Max Driveway Length', flags: { Electric: 'Electric' }, amps: 'Electrical Service', entry: 'Site Access' }, // wisconsin.goingtocamp.com
    mi: { len: 'Site Length', flags: { Electric: 'Electricity Available', Water: 'Water Hookup', Sewer: 'Sewer Hookup' },
          amps: 'Electrical Service', pull: 'Pull Through' },                                                          // midnrreservations.com
  },
  async start(key, cfg, gap = 500) {
    this.key = key; this.cfg = cfg; this.gap = gap;
    const f = await (await fetch('/api/attribute/filterable')).json(), arr = Array.isArray(f) ? f : Object.values(f);
    const nm = a => ((a.localizedValues || [{}])[0].displayName || '').trim();
    const A = n => { const a = n && arr.find(x => nm(x) === n); return a ? [a.attributeDefinitionId, Object.fromEntries((a.values || []).map(v => [v.enumValue, ((v.localizedValues || [{}])[0].displayName || '').trim()]))] : null; };
    this.A = { len: A(cfg.len), service: A(cfg.service), amps: A(cfg.amps), entry: A(cfg.entry), pull: A(cfg.pull),
               flags: Object.fromEntries(Object.entries(cfg.flags || {}).map(([k, n]) => [k, A(n)])) };
    if (!this.A.len) throw new Error('length attribute not found: ' + cfg.len);
    this.cats = Object.fromEntries((await (await fetch('/api/resourcecategory')).json()).map(c => [c.resourceCategoryId, ((c.localizedValues || [{}])[0].name || '').trim()]));
    this.locs = (await (await fetch('/api/resourceLocation')).json()).map(x => [x.resourceLocationId, ((x.localizedValues || [{}])[0].fullName || (x.localizedValues || [{}])[0].shortName || '').trim()]);
    const ls = JSON.parse(localStorage.getItem('gtc_' + key) || 'null');
    this.data = ls ? ls.data : {}; this.fail = 0;
    this.gen = (this.gen || 0) + 1; this.loop2(this.gen); return this.st2();
  },
  save() { localStorage.setItem('gtc_' + this.key, JSON.stringify({ data: this.data })); },
  read(res) {
    const da = res.definedAttributes || [], get = a => a ? (da.find(x => x.attributeDefinitionId === a[0]) || {}) : {};
    const en = a => a ? (get(a).values || []).map(v => a[1][v]).filter(Boolean).join('/') : '';
    const len = get(this.A.len).value;
    if (typeof len !== 'number' || !(len > 0)) return null;
    const amps = en(this.A.amps);
    let svc = en(this.A.service);
    if (!this.A.service) {
      const on = k => en(this.A.flags[k]).split('/').includes('Yes');
      svc = [on('Electric') || /\d/.test(amps) && !/none|not avail/i.test(amps) ? 'Electric' : 'No electric', on('Water') ? 'Water' : '', on('Sewer') ? 'Sewer' : ''].filter(Boolean).join(', ');
    }
    const entry = this.A.pull ? (en(this.A.pull) === 'Yes' ? 'Pull Thru' : 'Back-in') : en(this.A.entry);
    return [res.resourceId, len, this.cats[res.resourceCategoryId] || '', svc, amps, entry];
  },
  async loop2(g) {
    for (const [id] of this.locs) {
      if (this.gen !== g) return;
      if (this.data[id]) continue;
      this.cur = id; let j = null;
      for (let t = 0, w = 20000; t < 9 && !j; t++, w = Math.min(w * 2, 300000)) {
        try { const r = await fetch('/api/resourcelocation/resources?resourceLocationId=' + id); if (r.ok) j = await r.json(); else this.last = r.status; } catch (e) { this.last = 'err'; }
        if (!j) { this.waiting = w; await SLEEP(w); this.waiting = 0; }
      }
      if (this.gen !== g) return;
      if (!j) { this.fail++; continue; }
      this.data[id] = Object.values(j).map(r => this.read(r)).filter(Boolean);
      this.save(); await SLEEP(this.gap);
    }
    this.finished = true;
  },
  st2() { return { key: this.key, done: Object.keys(this.data).length, of: this.locs.length, sites: Object.values(this.data).reduce((a, b) => a + b.length, 0), fail: this.fail, waiting: this.waiting, last: this.last, finished: !!this.finished }; },
  agg() {
    const D = { C: [], S: [], M: [], E: [] }, ix = (d, v) => { let i = D[d].indexOf(v); if (i < 0) { i = D[d].length; D[d].push(v); } return i; };
    const names = Object.fromEntries(this.locs), seen = new Set(), lines = []; let n = 0, h = 0;
    for (const [lid, rows] of Object.entries(this.data)) {
      const c = {};
      for (const [rid, l, cat, s, m, e] of rows) {
        if (seen.has(rid)) continue; seen.add(rid);
        const k = [l, ix('C', cat), ix('S', s), ix('M', m), ix('E', e)].join(':'); c[k] = (c[k] || 0) + 1;
      }
      const ks = Object.entries(c); if (!ks.length) continue;
      for (const [k, v] of ks) { n += v; h = (h + k.split(':').reduce((a, b) => a * 31 + +b, 7) * v) % 1e9; }
      lines.push((names[lid] || lid).replace(/[|\n]/g, ' ') + '|' + ks.map(([k, v]) => k + ':' + v).join(','));
    }
    return { n, h, text: ['C|' + D.C.join('~'), 'S|' + D.S.join('~'), 'M|' + D.M.join('~'), 'E|' + D.E.join('~'), ...lines].join('\n') };
  }
};
