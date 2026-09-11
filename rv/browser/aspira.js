// Aspira ".page" systems (Colorado cpwshop.com, Kansas campitks.gov). Run in a tab on the booking site:
//   await AS.start('co', 50000, 50140)      AS.st() -> progress      AS.agg() -> {n, h, text}
// There is no public park list, so park ids are probed across a range. Per park: load campgroundDetails.page (sets the
// server-side park context; skipping it makes the next call 500), then campgroundMap.page for the map component id,
// then /ajax/CUIGISMap?event=getGISMap, whose GeoJSON features carry each site's type ("Full Hookup", "Electric", ...)
// and a "Maximum Vehicle Length" attribute. Colorado ids are 50000-50140, Kansas 519100-519175.
// agg(): T| site types, H| (same types, read for hookups), E| entry; then Park|len:type:hook:entry:count
window.SLEEP = window.SLEEP || (ms => new Promise(r => setTimeout(r, ms)));
window.AS = {
  async start(key, a, b, gap = 1500) {
    this.key = 'as_' + key; this.gap = gap; this.data = JSON.parse(localStorage.getItem(this.key) || '{}');
    this.a = a; this.b = b; this.run(); return this.st();
  },
  async gis(pid) {
    await fetch('/camping/x/r/campgroundDetails.page?parkID=' + pid);
    const h = await (await fetch('/campgroundMap.page?parkID=' + pid)).text();
    const cid = (h.match(/componentId=(ac-[\w-]+)/) || h.match(/"(ac-[0-9a-f]{6,})"/) || [])[1];
    if (!cid) return null;
    const t = await (await fetch('/ajax/CUIGISMap?event=getGISMap&componentId=' + cid + '&e_Page_ID=/campgroundMap.page')).text();
    try { return JSON.parse(t); } catch (e) { return null; }
  },
  async run() {
    for (let pid = this.a; pid <= this.b; pid++) {
      this.cur = pid; if (this.data[pid]) continue;
      let j = null; try { j = await this.gis(pid); } catch (e) {}
      if (j && j.location && j.markersUnique) {
        const rows = [];
        for (const f of j.markersUnique.features || []) {
          const u = f.properties && f.properties.uiData; if (!u) continue;
          const attrs = (u.sections || []).flatMap(s => s.attributes || []);
          const len = +((attrs.find(x => /Vehicle Length|Driveway Length|Equipment Length/i.test(x.title || '')) || {}).value || 0);
          const ty = ((u.head || {}).siteType || '').replace(/<[^>]+>/g, '').replace(/^Site type:\s*/, '').trim();
          const ent = ((attrs.find(x => /Driveway Entry|Entry/i.test(x.title || '')) || {}).value || '');
          if (len > 0) rows.push([len, ty, ent]);
        }
        this.data[pid] = [j.location.name, rows]; localStorage.setItem(this.key, JSON.stringify(this.data));
      }
      await SLEEP(this.gap);
    }
    this.finished = true;
  },
  st() { return { cur: this.cur, parks: Object.values(this.data).filter(x => x[1].length).length, sites: Object.values(this.data).reduce((a, x) => a + x[1].length, 0), finished: !!this.finished }; },
  agg() {
    const D = { T: [], H: [], E: [] }, ix = (d, v) => { let i = D[d].indexOf(v); if (i < 0) { i = D[d].length; D[d].push(v); } return i; };
    const lines = []; let n = 0, h = 0;
    for (const [, [name, rows]] of Object.entries(this.data)) {
      if (!rows.length) continue;
      const c = {};
      for (const [L, t, e] of rows) { const k = [L, ix('T', t), ix('H', t), ix('E', e)].join(':'); c[k] = (c[k] || 0) + 1; }
      const ks = Object.entries(c);
      for (const [k, v] of ks) { n += v; h = (h + k.split(':').reduce((a, b) => a * 31 + +b, 7) * v) % 1e9; }
      lines.push(name.replace(/[|\n]/g, ' ') + '|' + ks.map(([k, v]) => k + ':' + v).join(','));
    }
    return { n, h, text: ['T|' + D.T.join('~'), 'H|' + D.H.join('~'), 'E|' + D.E.join('~'), ...lines].join('\n') };
  }
};
