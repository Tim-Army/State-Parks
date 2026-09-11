// Itinio per-site scraper (TN, SC, AL, AR). Run in a tab on the state's reserve.* host:
//   await IT.start('al', ['extra-slug', ...])     IT.st2() -> progress     IT.agg() -> {n, h, text}
// One form POST per park (stage=1, view=parkwide) returns every site as a <td data-site=...> carrying
// data-maxrv, data-drivelength, data-access, data-electric, data-water, data-sewer.
// Running in the page (rather than curl) gets past the AWS WAF JavaScript challenge some hosts serve.
// agg(): T| site labels, H| hookup text, E| access; then Park|len:label:hook:entry:count
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
window.IT = {
  SKIP: new Set(['guest', 'account', 'myaccount', 'cart', 'login', 'logout', 'search', 'help', 'faq', 'contact', 'privacy', 'terms',
                 'gallery', 'register', 'checkout', 'reservations', 'gift-cards', 'giftcards', 'about', 'home', 'map', 'maps', 'lodging', 'events', 'cancel']),
  async start(key, extra = [], gap = 1500) {
    this.key = key; this.gap = gap;
    const home = await (await fetch('/')).text(), slugs = [];
    const add = s => { if (s && !this.SKIP.has(s) && !slugs.includes(s)) slugs.push(s); };
    for (const m of home.matchAll(/href="(?:https:\/\/[^"/]+)?\/([a-z0-9][a-z0-9-]+)(?:\/(?:camping|campsites))?\/?"/g)) add(m[1]);
    for (const m of home.matchAll(/<option value="([a-z0-9][a-z0-9-]+)"/g)) add(m[1]);
    extra.forEach(add);
    this.slugs = slugs;
    const ls = JSON.parse(localStorage.getItem('it_' + key) || 'null');
    this.data = ls ? ls.data : {}; this.done = new Set(ls ? ls.done : []);
    const d = new Date(Date.now() + 40 * 864e5); while (d.getDay() !== 2) d.setDate(d.getDate() + 1);
    const f = x => String(x.getMonth() + 1).padStart(2, '0') + '/' + String(x.getDate()).padStart(2, '0') + '/' + x.getFullYear();
    this.d1 = f(d); d.setDate(d.getDate() + 2); this.d2 = f(d);
    this.gen = (this.gen || 0) + 1; this.loop2(this.gen); return this.st2();
  },
  save() { localStorage.setItem('it_' + this.key, JSON.stringify({ data: this.data, done: [...this.done] })); },
  async get(url, body) {
    for (let t = 0, w = 20000; t < 6; t++, w = Math.min(w * 2, 300000)) {
      try {
        const r = await fetch(url, body ? { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams(body) } : {});
        if (r.ok || r.status === 404) return r.ok ? await r.text() : '';
        this.last = r.status;
      } catch (e) { this.last = 'err'; }
      this.waiting = w; await SLEEP(w); this.waiting = 0;
    }
    return '';
  },
  attrs(tag) {
    const o = {}, t = document.createElement('textarea');
    for (const m of tag.matchAll(/data-([a-z0-9]+)="([^"]*)"/g)) { t.innerHTML = m[2]; o[m[1]] = t.value; }
    return o;
  },
  async loop2(g) {
    for (const slug of this.slugs) {
      if (this.gen !== g) return;
      if (this.done.has(slug)) continue;
      this.cur = slug; let url, p, tok, pid;
      for (const sub of ['camping', 'campsites']) {
        url = `/${slug}/${sub}`; p = await this.get(url);
        tok = p.match(/name="csrfToken"[^>]*value="([^"]*)"/); pid = p.match(/name="parkid"[^>]*value="([^"]*)"/);
        if (tok && pid) break;
        await SLEEP(500);
      }
      if (tok && pid) {
        const tm = p.match(/<title>\s*([^<|–-]+)/), name = tm ? tm[1].trim() : slug;
        await SLEEP(this.gap);
        const h = await this.get(url, { csrfToken: tok[1], stage: '1', view: 'parkwide', processing: 'true', startOver: 'false',
                                         reserve: 'false', checkin: this.d1, checkout: this.d2, parkid: pid[1] });
        const seen = {};
        for (const m of h.matchAll(/<t[dr]\b[^>]*data-maxrv=[^>]*>/g)) {          // TN/SC/AL: <td data-site>, AR: <tr data-description>
          const a = this.attrs(m[0]), key = (a.description || a.site || '').trim();
          if (!key || seen[key]) continue;
          const yes = k => /^(yes|true)$/i.test(a[k] || ''), amp = /^(|false|no|none)$/i.test(a.electric || '') ? '' : a.electric;
          const L = ['maxrv', 'drivelength', 'parklength'].map(k => +(/^\d+$/.test(a[k] || '') ? a[k] : 0)).find(x => x > 0) || 0;
          seen[key] = [L, (a.site || a.description || '').replace(/\d+[A-Z]?\b/g, '').replace(/^[\s#-]+|[\s#-]+$/g, ''),
                       [amp && (/amp/i.test(amp) ? amp : amp + ' Amp'), yes('water') ? 'Water' : '', yes('sewer') ? 'Sewer' : ''].filter(Boolean).join(';'), a.access || ''];
        }
        const rows = Object.values(seen).filter(r => r[0] > 0);
        if (rows.length) this.data[name] = rows;
      }
      this.done.add(slug); this.save(); await SLEEP(this.gap);
    }
    this.finished = true;
  },
  st2() { return { key: this.key, done: this.done.size, of: this.slugs.length, parks: Object.keys(this.data).length, sites: Object.values(this.data).reduce((a, b) => a + b.length, 0), waiting: this.waiting, last: this.last, finished: !!this.finished }; },
  agg() {
    const D = { T: [], H: [], E: [] }, ix = (d, v) => { let i = D[d].indexOf(v); if (i < 0) { i = D[d].length; D[d].push(v); } return i; };
    const lines = []; let n = 0, h = 0;
    for (const [park, rows] of Object.entries(this.data)) {
      const c = {};
      for (const [L, t, hk, e] of rows) { const k = [L, ix('T', t), ix('H', hk), ix('E', e)].join(':'); c[k] = (c[k] || 0) + 1; }
      const ks = Object.entries(c);
      for (const [k, v] of ks) { n += v; h = (h + k.split(':').reduce((a, b) => a * 31 + +b, 7) * v) % 1e9; }
      lines.push(park.replace(/[|\n]/g, ' ') + '|' + ks.map(([k, v]) => k + ':' + v).join(','));
    }
    return { n, h, text: ['T|' + D.T.join('~'), 'H|' + D.H.join('~'), 'E|' + D.E.join('~'), ...lines].join('\n') };
  }
};
