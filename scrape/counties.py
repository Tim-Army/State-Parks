#!/usr/bin/env python3
"""Add a County column to parks.csv.

Sources, in priority order:
  1. scrape/county-overrides.csv — hand-checked lists (e.g. Alabama, from the state's own park list)
  2. Wikidata — state park / state forest / state historic site / state recreation area items matched by name
     within the state; county from the item's coordinates (FCC Census Area API) plus its "located in" counties
  3. OpenStreetMap Nominatim — name search limited to the park's state; county from the result's address,
     or from its coordinates via the FCC API
Parks spanning several counties list them comma-separated; point-based sources only know the county where
the park's mapped point sits.

Inputs are the JSON caches built during collection (see the functions below); this script only merges.
Usage: python3 scrape/counties.py <cache-dir>
"""
import csv, json, os, re, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
D = sys.argv[1]
SUFFIX = re.compile(r'\s+(County|Parish|Borough|City and Borough|Census Area|Municipality)$')

def clean(c):
    c = SUFFIX.sub('', (c or '').replace('\u02bb', '').replace('\u2018', '').strip())
    return re.sub(r'^City of\s+', '', c)

def uniq(xs):
    out = []
    for x in map(clean, xs):
        if x and x not in out: out.append(x)
    return out

def fcc(lat, lon, cache):
    k = f'{float(lat):.5f},{float(lon):.5f}'
    if k not in cache:
        try:
            with urllib.request.urlopen(f'https://geo.fcc.gov/api/census/area?lat={lat}&lon={lon}&format=json', timeout=30) as r:
                res = json.load(r).get('results') or []
                cache[k] = [res[0]['county_name'], res[0]['state_name']] if res else []
        except Exception:
            return None
    return cache[k]

over = {}
op = os.path.join(HERE, 'county-overrides.csv')
if os.path.exists(op):
    for r in csv.DictReader(open(op, encoding='utf-8')):
        over[(r['State'], r['Park Name'])] = r['County']
wd = json.load(open(os.path.join(D, 'res_wd.json')))
nomi = json.load(open(os.path.join(D, 'nomi.json'))) if os.path.exists(os.path.join(D, 'nomi.json')) else {}
fc_path = os.path.join(D, 'fcc_pts.json')
fcache = json.load(open(fc_path)) if os.path.exists(fc_path) else {}

rows = list(csv.DictReader(open(os.path.join(ROOT, 'parks.csv'), encoding='utf-8')))
stats = {'override': 0, 'wikidata': 0, 'osm': 0, 'none': 0}
for r in rows:
    k = (r['State'], r['Park Name']); kk = '|'.join(k)
    county = ''
    if k in over:
        county, src = over[k], 'override'
    elif kk in wd and wd[kk]['counties']:
        county, src = ', '.join(uniq(wd[kk]['counties'])[:4]), 'wikidata'
    elif nomi.get(kk):
        h = nomi[kk][0]
        c = h.get('county') or ''
        if not c:
            v = fcc(h['lat'], h['lon'], fcache)
            if v and v[1] == r['State']: c = v[0]
        county, src = clean(c), 'osm'
    if not county: src = 'none'
    stats[src] += 1
    r['County'] = county
json.dump(fcache, open(fc_path, 'w'))
with open(os.path.join(ROOT, 'parks.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=['State', 'Park Name', 'County', 'Official Website']); w.writeheader(); w.writerows(rows)
print(stats, len(rows))
