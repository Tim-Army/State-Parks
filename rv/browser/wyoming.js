// Wyoming (US eDirect) — its search/grid returns VehicleLength 0 for every unit, so the length has to come from the
// per-unit details call: search/details/{unitId}/startdate/{YYYY-MM-DD}/nights/1/0/0 -> Amenities["0.Unit&parkingsize"]
// ("Total Vehicle and Equipment available parking in feet"), PullInTypeName, and electricity/water/sewer amenities.
// One call per unit, so this is the slowest scraper. Run in a tab on reserve.wyoming.gov:
//   await WY.init(); WY.run();     WY.st() -> progress     WY.agg() -> {n, h, text}
window.SLEEP = window.SLEEP || (ms => new Promise(r => setTimeout(r, ms)));
window.WY = {
  B: 'https://wyordr.usedirect.com/wyomingrdr/rdr/',
  D: new Date(Date.now() + 45 * 864e5).toISOString().slice(0, 10),
  async init() {
    const s = JSON.parse(localStorage.getItem('wy') || 'null') || {};
    this.facs = await (await fetch(this.B + 'fd/facilities')).json();
    this.places = Object.fromEntries((await (await fetch(this.B + 'fd/places')).json()).map(p => [p.PlaceId, p.Name]));
    this.types = Object.fromEntries((await (await fetch(this.B + 'fd/unittypes')).json()).map(t => [t.UnitTypeId, t.Name]));
    this.units = s.units || {}; this.fdone = new Set(s.fdone || []); this.rows = s.rows || {};
  },
  save() { localStorage.setItem('wy', JSON.stringify({ units: this.units, fdone: [...this.fdone], rows: this.rows })); },
  async j(url, body) {
    for (let t = 0, w = 15000; t < 7; t++, w = Math.min(w * 2, 240000)) {
      try { const r = await fetch(url, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {}); if (r.ok) return await r.json(); this.last = r.status; } catch (e) { this.last = 'err'; }
      await SLEEP(w);
    }
    return null;
  },
  async run() {
    for (const f of this.facs) {
      if (this.fdone.has(f.FacilityId)) continue;
      const g = await this.j(this.B + 'search/grid', { FacilityId: f.FacilityId, StartDate: this.D, Nights: '1', UnitSort: 'orderby', InSeasonOnly: false, WebOnly: false, IsADA: false, UnitCategoryId: 0, SleepingUnitId: 0, MinVehicleLength: 0, UnitTypesGroupIds: [], UnitTypeIds: [] });
      if (g) { for (const u of Object.values((g.Facility || {}).Units || {})) if (!this.units[u.UnitId]) this.units[u.UnitId] = [f.PlaceId, u.UnitTypeId]; this.fdone.add(f.FacilityId); this.save(); }
      await SLEEP(700);
    }
    for (const [uid, [pid, tid]] of Object.entries(this.units)) {
      if (this.rows[uid]) continue;
      const d = await this.j(this.B + `search/details/${uid}/startdate/${this.D}/nights/1/0/0`);
      if (d) {
        const A = Object.values(d.Amenities || {}), val = rx => (A.find(a => rx.test(a.ShortName || a.Name || '')) || {}).Value;
        const L = parseInt(val(/parkingsize/i) || '0') || 0, amp = val(/Amp/i) || '';
        const e = val(/^Electricity$/i) === '1' || /\d/.test(amp);
        const on = rx => { const v = (A.find(a => rx.test(a.Name) && !/distance/i.test(a.Name)) || {}).Value; return v === '1' || /yes/i.test(v || ''); };
        const hook = [e ? (/\d/.test(amp) ? amp + ' Amp' : 'Electric') : '', on(/water/i) ? 'Water' : '', on(/sewer/i) ? 'Sewer' : ''].filter(Boolean).join(';');
        this.rows[uid] = [L, pid, tid, hook, d.PullInTypeName || ''];
      } else this.rows[uid] = [0];
      if (Object.keys(this.rows).length % 10 === 0) this.save();
      await SLEEP(600);
    }
    this.save(); this.finished = true;
  },
  st() { return { fdone: this.fdone.size, facs: this.facs.length, units: Object.keys(this.units).length, rows: Object.keys(this.rows).length, withLen: Object.values(this.rows).filter(r => r[0] > 0).length, last: this.last, finished: !!this.finished }; },
  agg() {
    const D = { T: [], H: [], E: [] }, ix = (d, v) => { let i = D[d].indexOf(v); if (i < 0) { i = D[d].length; D[d].push(v); } return i; };
    const by = {};
    for (const r of Object.values(this.rows)) {
      if (!(r[0] > 0)) continue;
      const [L, pid, tid, hook, pull] = r, pk = (this.places[pid] || 'Place ' + pid).replace(/[|\n]/g, ' ').trim();
      const k = [L, ix('T', this.types[tid] || ''), ix('H', hook), ix('E', pull)].join(':');
      (by[pk] = by[pk] || {})[k] = ((by[pk] || {})[k] || 0) + 1;
    }
    let n = 0, h = 0; const lines = [];
    for (const [pk, o] of Object.entries(by)) {
      const ks = Object.entries(o);
      for (const [k, v] of ks) { n += v; h = (h + k.split(':').reduce((a, b) => a * 31 + +b, 7) * v) % 1e9; }
      lines.push(pk + '|' + ks.map(([k, v]) => k + ':' + v).join(','));
    }
    return { n, h, text: ['T|' + D.T.join('~'), 'H|' + D.H.join('~'), 'E|' + D.E.join('~'), ...lines].join('\n') };
  }
};
