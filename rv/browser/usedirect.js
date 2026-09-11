// US eDirect / Tyler per-site scraper (CA, FL, OH, AZ, NV, VA, IL, MO, ND).
// Run in a tab on the state's reservation site (same origin as its API, or one the API allows via CORS):
//   await UD.start('ca', 'https://california-rdr.prod.cali.rd12.recreation-management.tylerapp.com/rdr/')
//   UD.st2()            -> progress
//   UD.agg()            -> {n, h, text}: rv/sites/<st>.txt contents ("T|" site-type dictionary, then
//                          Park|len:type:pull:count,...); n = sites, h = checksum checked by rv/sites/chk.py
// The API base is in globalThis.apiurl or /config.json (rdrApiUrl) on each state's booking site.
// Ohio also sells marina docks/moorings with vehicle lengths through the same endpoint: pass {ohioFilter:true}
// to drop every unit that appears in a non-camping facility.
// Pacing: 0.8 s between facilities; a 403 means the API's burst limit, so wait it out (20 s doubling to 5 min).
// Timers run in a Web Worker because Chrome throttles timers in background tabs to about one per minute.
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
window.UD = {
  async start(key, B, opt = {}) {
    this.key = key; this.B = B; this.gap = opt.gap || 800; this.ohio = !!opt.ohioFilter;
    this.D = new Date(Date.now() + 45 * 864e5).toISOString().slice(0, 10);
    const ls = k => JSON.parse(localStorage.getItem(key + k) || 'null');
    this.facs = ls('_f') || await (await fetch(B + 'fd/facilities')).json();
    this.places = ls('_p') || Object.fromEntries((await (await fetch(B + 'fd/places')).json()).map(p => [p.PlaceId, p.Name]));
    this.types = ls('_t') || Object.fromEntries((await (await fetch(B + 'fd/unittypes')).json()).map(t => [t.UnitTypeId, t.Name]));
    this.units = ls('_u') || {}; this.drop = ls('_x') || {}; this.done = new Set(ls('_d') || []);
    this.gen = (this.gen || 0) + 1; this.loop2(this.gen); return this.st2();
  },
  save() {
    const k = this.key, s = (a, v) => localStorage.setItem(k + a, JSON.stringify(v));
    s('_f', this.facs); s('_p', this.places); s('_t', this.types); s('_u', this.units); s('_x', this.drop); s('_d', [...this.done]);
  },
  RX: /pier|mooring|dock|marina|slip|boat|buoy|wharf|auxiliary|parking|causeway|ramp/i,
  INC: /camp|loop|\brv\b|tent|yurt|cottage|cabin|equestrian|horse|sites?\b/i,
  async grid2(f) {
    for (let t = 0, w = 20000; t < 9; t++, w = Math.min(w * 2, 300000)) {
      try {
        const r = await fetch(this.B + 'search/grid', { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ FacilityId: f.FacilityId, StartDate: this.D, Nights: '1', UnitSort: 'orderby', InSeasonOnly: false, WebOnly: false, IsADA: false, UnitCategoryId: 0, SleepingUnitId: 0, MinVehicleLength: 0, UnitTypesGroupIds: [], UnitTypeIds: [] }) });
        if (r.ok) return Object.values(((await r.json()).Facility || {}).Units || {});
        this.last = r.status;
      } catch (e) { this.last = 'err'; }
      this.waiting = w; await SLEEP(w); this.waiting = 0;
    }
    return null;
  },
  async loop2(g) {
    for (let i = 0; i < this.facs.length; i++) {
      if (this.gen !== g) return;
      if (this.done.has(i)) continue;
      const f = this.facs[i]; this.cur = i;
      const u = await this.grid2(f);
      if (this.gen !== g) return;
      if (u !== null) {
        const bad = this.ohio && (this.RX.test(f.Name) || !this.INC.test(f.Name));
        for (const v of u) {
          if (v.UnitId == null) continue;
          if (bad) { this.drop[v.UnitId] = 1; continue; }
          if (typeof v.VehicleLength === 'number' && v.VehicleLength > 0 && !this.units[v.UnitId])
            this.units[v.UnitId] = [f.PlaceId, v.VehicleLength, v.UnitTypeId, v.Name, v.IsAda ? 1 : 0];
        }
        this.done.add(i);
      } else this.gaveUp = (this.gaveUp || 0) + 1;
      this.save(); await SLEEP(this.gap);
    }
    this.save(); this.finished = true;
  },
  st2() { return { key: this.key, done: this.done.size, of: this.facs.length, cur: this.cur, units: Object.keys(this.units).length, waiting: this.waiting, last: this.last, gaveUp: this.gaveUp || 0, finished: !!this.finished }; },
  agg() {
    const T = [], ti = {}, by = {}; let n = 0, h = 0;
    for (const [id, [p, l, t, nm]] of Object.entries(this.units)) {
      if (this.drop[id]) continue;
      const tn = (this.types[t] || '') + '';
      if (!(tn in ti)) { ti[tn] = T.length; T.push(tn.trim()); }
      const k = l + ':' + ti[tn] + ':' + (/pull/i.test(nm + ' ' + tn) ? 1 : 0);
      const pk = (this.places[p] || 'Place ' + p).replace(/[|\n]/g, ' ').trim();
      (by[pk] = by[pk] || {})[k] = ((by[pk] || {})[k] || 0) + 1;
    }
    const L = [];
    for (const [pk, o] of Object.entries(by)) {
      const e = Object.entries(o);
      for (const [k, v] of e) { n += v; h = (h + k.split(':').reduce((a, b) => a * 31 + +b, 7) * v) % 1e9; }
      L.push(pk + '|' + e.map(([k, v]) => k + ':' + v).join(','));
    }
    return { n, h, text: 'T|' + T.join('~') + '\n' + L.join('\n') };
  }
};
