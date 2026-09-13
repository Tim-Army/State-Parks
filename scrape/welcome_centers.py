#!/usr/bin/env python3
"""Fill the "Welcome Center" column of parks.csv from scrape/welcome-center-overrides.csv.

The column holds the park's published physical address — the welcome center / park office address given on the
park's own website. Values come from, in priority order:
  1. scrape/welcome-center-overrides.csv (State, Park Name, Welcome Center, Source) — hand-verified
  2. the crawl cache written by scrape/addresses.py, after its boilerplate and in-state checks
  3. the reservation-system cache written by scrape/addr_reservations.py, matched by normalized park name

Usage: python3 scrape/welcome_centers.py [<addresses-cache-dir>]
"""
import csv, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
COL = 'Welcome Center'
VCOL = 'Visitor Center?'

over = {}
p = os.path.join(HERE, 'welcome-center-overrides.csv')
if os.path.exists(p):
    for r in csv.DictReader(open(p, encoding='utf-8')):
        if r.get('Park Name'): over[(r['State'], r['Park Name'])] = (r.get('Welcome Center') or '').strip()

def norm(s):
    s = re.sub(r'\s+(State (Park|Forest|Recreation Area|Historic(al)? (Site|Park)|Natural Area|Beach|Trail|Wayside)|SP|SRA|SHS)$', '', s.strip(), flags=re.I)
    return re.sub(r'[^a-z0-9]', '', s.lower())

crawl, res, vcs = {}, {}, {}
if len(sys.argv) > 1:
    sys.path.insert(0, HERE)
    import addresses, json
    cp = os.path.join(sys.argv[1], 'addr.json')
    if os.path.exists(cp):
        allrows = list(csv.DictReader(open(os.path.join(ROOT, 'parks.csv'), encoding='utf-8')))
        cache = json.load(open(cp))
        crawl = addresses.usable(allrows, cache)
        # "Yes"/"No" from the crawler, but only where the answer is trustworthy:
        #  - the page has to have yielded something (an address or a centre mention); a page whose text never
        #    rendered would otherwise read as a confident "No"
        #  - a state whose every park says "Yes" is a site template, not 3,519 visitor centres (Ohio, West
        #    Virginia and Wyoming mention one on every page), so that state is left blank
        raw = {}
        for r in allrows:
            v = cache.get(r['Official Website']) or []
            how = v[1] if len(v) > 1 else ''
            if len(v) > 3 and v[3] and (how in ('schema', 'center', 'page', 'browser')):
                raw[(r['State'], r['Park Name'])] = v[3]
        tally = {}
        for (st, _), v in raw.items():
            y, n = tally.get(st, (0, 0))
            tally[st] = (y + (v == 'Yes'), n + 1)
        template = {st for st, (y, n) in tally.items() if n >= 10 and y / n >= 0.95}
        vcs = {k: v for k, v in raw.items() if k[0] not in template}
        if template: print('left blank (site template mentions a centre on every page):', ', '.join(sorted(template)))
    rp = os.path.join(sys.argv[1], 'addr_res.json')
    if os.path.exists(rp):
        for k, v in json.load(open(rp)).items():
            st, nm = k.split('|', 1)
            res[(st, norm(nm))] = v

ABBR = {'Alabama':'AL','Alaska':'AK','Arizona':'AZ','Arkansas':'AR','California':'CA','Colorado':'CO','Connecticut':'CT','Delaware':'DE','Florida':'FL','Georgia':'GA','Hawaii':'HI','Idaho':'ID','Illinois':'IL','Indiana':'IN','Iowa':'IA','Kansas':'KS','Kentucky':'KY','Louisiana':'LA','Maine':'ME','Maryland':'MD','Massachusetts':'MA','Michigan':'MI','Minnesota':'MN','Mississippi':'MS','Missouri':'MO','Montana':'MT','Nebraska':'NE','Nevada':'NV','New Hampshire':'NH','New Jersey':'NJ','New Mexico':'NM','New York':'NY','North Carolina':'NC','North Dakota':'ND','Ohio':'OH','Oklahoma':'OK','Oregon':'OR','Pennsylvania':'PA','Rhode Island':'RI','South Carolina':'SC','South Dakota':'SD','Tennessee':'TN','Texas':'TX','Utah':'UT','Vermont':'VT','Virginia':'VA','Washington':'WA','West Virginia':'WV','Wisconsin':'WI','Wyoming':'WY'}

def abbrev(a, state):
    """Reservation feeds spell the state out ("..., Argyle, Minnesota 56713"); use the postal abbreviation."""
    return re.sub(r',?\s+' + re.escape(state) + r'\s+(\d{5})', f', {ABBR.get(state, state)} \\1', a) if state in ABBR else a

rows = list(csv.DictReader(open(os.path.join(ROOT, 'parks.csv'), encoding='utf-8')))
fields = list(rows[0].keys())
if COL not in fields: fields.insert(fields.index('County') + 1, COL)
if VCOL not in fields: fields.insert(fields.index(COL) + 1, VCOL)
n = 0
for r in rows:
    v = (over.get((r['State'], r['Park Name'])) or crawl.get((r['State'], r['Park Name']))
         or res.get((r['State'], norm(r['Park Name']))) or '')
    r[COL] = abbrev(v, r['State']) if v else ''
    r[VCOL] = vcs.get((r['State'], r['Park Name']), '')
    if v: n += 1
with open(os.path.join(ROOT, 'parks.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)
print(f'{n} of {len(rows)} parks have a welcome center recorded')
