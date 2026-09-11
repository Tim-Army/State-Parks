#!/usr/bin/env python3
"""Regenerate index.html and the derived CSVs from the source data.

Inputs:  parks.csv, state-park-systems.csv, rv-policies.csv, virginia-rv-site-sizes.csv,
         rv/site-combos.csv (state parks, from rv/build_sites.py),
         federal/federal-combos.csv (federal campgrounds, from federal/build_ridb.py)
Outputs: index.html, campsite-rv-lengths.csv, campsite-rv-summary.csv, federal-rv-summary.csv,
         and the two measured columns of rv-policies.csv.

Run: python3 build_site.py
"""
import csv, json, html, os, re, statistics, collections, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
P = lambda *a: os.path.join(ROOT, *a)
esc = lambda s: html.escape(str(s), quote=True)

def rows(path):
    with open(P(path), newline='', encoding='utf-8') as fh:
        return list(csv.DictReader(fh))

ABBR = {'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California', 'CO': 'Colorado',
        'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
        'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana',
        'ME': 'Maine', 'MD': 'Maryland', 'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota',
        'MS': 'Mississippi', 'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
        'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina',
        'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania',
        'RI': 'Rhode Island', 'SC': 'South Carolina', 'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas',
        'UT': 'Utah', 'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
        'WI': 'Wisconsin', 'WY': 'Wyoming'}
AGENCY = {'USACE': 'Army Corps of Engineers', 'FS': 'Forest Service', 'NPS': 'National Park Service',
          'BLM': 'Bureau of Land Management', 'BOR': 'Bureau of Reclamation'}
# Where to book, per state (the public booking site the data came from).
BOOK = {'Arizona': 'https://azstateparks.com/', 'California': 'https://www.reservecalifornia.com/',
        'Delaware': 'https://delawarestateparks.reserveamerica.com/', 'Florida': 'https://www.floridastateparks.org/',
        'Georgia': 'https://gastateparks.reserveamerica.com/', 'Illinois': 'https://dnr.illinois.gov/parks.html',
        'Iowa': 'https://iowastateparks.reserveamerica.com/', 'Maryland': 'https://parkreservations.maryland.gov/',
        'Michigan': 'https://midnrreservations.com/', 'Missouri': 'https://icampmo1.usedirect.com/',
        'Montana': 'https://montanastateparks.reserveamerica.com/', 'Nebraska': 'https://nebraskastateparks.reserveamerica.com/',
        'Nevada': 'https://parks.nv.gov/', 'New Mexico': 'https://newmexicostateparks.reserveamerica.com/',
        'New York': 'https://newyorkstateparks.reserveamerica.com/', 'North Carolina': 'https://northcarolinastateparks.reserveamerica.com/',
        'North Dakota': 'https://reservendparks.com/', 'Ohio': 'https://ohiodnr.gov/go-and-do/plan-a-visit/find-a-property',
        'Oregon': 'https://oregonstateparks.reserveamerica.com/', 'Texas': 'https://texasstateparks.reserveamerica.com/',
        'Utah': 'https://utahstateparks.reserveamerica.com/', 'Virginia': 'https://reservevaparks.com/',
        'Washington': 'https://washington.goingtocamp.com/', 'Wisconsin': 'https://wisconsin.goingtocamp.com/',
        'Tennessee': 'https://reserve.tnstateparks.com/', 'South Carolina': 'https://reserve.southcarolinaparks.com/',
        'Arkansas': 'https://reserve.arkansasstateparks.com/', 'Kentucky': 'https://kentuckystateparks.reserveamerica.com/',
        'Indiana': 'https://indianastateparks.reserveamerica.com/', 'Vermont': 'https://vtstateparks-visit.com/',
        'Pennsylvania': 'https://pennsylvaniastateparks.reserveamerica.com/', 'Oklahoma': 'https://okstateparks.reserveamerica.com/',
        'Connecticut': 'https://connecticutstateparks.reserveamerica.com/', 'New Hampshire': 'https://newhampshirestateparks.reserveamerica.com/',
        'Rhode Island': 'https://rhodeislandstateparks.reserveamerica.com/', 'Massachusetts': 'https://massdcrcamping.reserveamerica.com/',
        'Alaska': 'https://alaskastateparks.reserveamerica.com/', 'South Dakota': 'https://reservations.gooutdoorssouthdakota.com/',
        'Louisiana': 'https://reservations.gooutdoorslouisiana.com/', 'Minnesota': 'https://reservemn.usedirect.com/MinnesotaWeb/',
        'Wyoming': 'https://reserve.wyoming.gov/web/', 'Colorado': 'https://www.cpwshop.com/camping.page',
        'Kansas': 'https://www.campitks.gov/camping.page'}
HK = {'?': -1, 'N': 0, 'E': 1, 'WE': 2, 'F': 3}
EN = {'B': 0, 'L': 0, 'P': 1, '?': 2}
BUCKETS = [(0, 25), (25, 35), (35, 45), (45, 60), (60, 10**6)]

def fmt(n): return f'{n:,}'

# ---------------------------------------------------------------- load
parks = rows('parks.csv')
systems = rows('state-park-systems.csv')
policies = rows('rv-policies.csv')
virginia = rows('virginia-rv-site-sizes.csv')
state_combos = rows('rv/site-combos.csv')
fed_combos = rows('federal/federal-combos.csv')
# check-in / check-out: per campground for federal (Recreation.gov), per state system for state parks (official policy pages)
fed_times = {r['RIDB Facility ID']: (r['Check-in'], r['Check-out']) for r in rows('federal/federal-times.csv')}
state_times = {r['State']: r for r in rows('rv/checkin-times.csv')} if os.path.exists(P('rv/checkin-times.csv')) else {}
def st_time(st, k):
    v = (state_times.get(st, {}).get(k) or '').strip()
    return 'Varies' if v.lower().startswith('varies') else '' if v.lower().startswith('not stated') else v

# group combos by park
def group(combos, key, extra):
    g = collections.OrderedDict()
    for r in combos:
        k = key(r)
        if k not in g: g[k] = dict(extra(r), c=[])
        g[k]['c'].append((int(r['Max Length (ft)']), r['Hookups'], int(r['Amps']), r['Entry'], int(r['Sites'])))
    return g

sp = group(state_combos, lambda r: (r['State'], r['Park']), lambda r: dict(state=r['State'], name=r['Park'], ag=''))
fp = group(fed_combos, lambda r: r['RIDB Facility ID'],
           lambda r: dict(state=ABBR.get(r['State'], r['State']), name=r['Campground'], ag=r['Agency'], fid=r['RIDB Facility ID']))
fp = collections.OrderedDict((k, v) for k, v in fp.items() if v['state'] in ABBR.values())

def lengths(c):
    L = []
    for ln, _, _, _, n in c: L += [ln] * n
    return sorted(L)

def stats(c):
    L = lengths(c); n = len(L)
    return dict(n=n, lo=L[0], hi=L[-1], avg=round(sum(L) / n), med=int(statistics.median(L)),
                b=[sum(1 for x in L if a <= x < b) for a, b in BUCKETS],
                elec=sum(k[4] for k in c if k[1] in ('E', 'WE', 'F')), full=sum(k[4] for k in c if k[1] == 'F'),
                hk_known=sum(k[4] for k in c if k[1] != '?'), pull=sum(k[4] for k in c if k[3] == 'P'),
                en_known=sum(k[4] for k in c if k[3] != '?'))

# ---------------------------------------------------------------- derived CSVs
per_park = []
for p in sp.values():
    s = stats(p['c']); p['s'] = s
    per_park.append([p['state'], p['name'], s['n'], s['lo'], s['hi'], s['avg'], s['med'], *s['b'], s['elec'], s['full'], s['pull']])
per_park.sort(key=lambda r: (r[0], r[1].lower()))
with open(P('campsite-rv-lengths.csv'), 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['State', 'Park', 'RV Sites', 'Shortest', 'Longest', 'Average', 'Median', 'Under 25 ft', '25-34', '35-44', '45-59', '60+',
                'With Electric', 'Full Hookup', 'Pull-Through'])
    w.writerows(per_park)

def rollup(groups):
    by = collections.defaultdict(list)
    for p in groups: by[p['state']].append(p)
    out = {}
    for st, ps in sorted(by.items()):
        allc = [k for p in ps for k in p['c']]
        out[st] = dict(stats(allc), parks=len(ps))
    return out

state_sum = rollup(sp.values())
fed_sum = rollup(fp.values())

def write_summary(path, summ, label):
    with open(P(path), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['State', label, 'RV Sites', 'Average (ft)', 'Median (ft)', 'Longest (ft)', 'Under 25 ft', '25-34', '35-44', '45-59', '60+',
                    'With Electric', 'Full Hookup', 'Pull-Through'])
        for st, s in summ.items():
            w.writerow([st, s['parks'], s['n'], s['avg'], s['med'], s['hi'], *s['b'], s['elec'], s['full'], s['pull']])
write_summary('campsite-rv-summary.csv', state_sum, 'Parks')
write_summary('federal-rv-summary.csv', fed_sum, 'Campgrounds')

# rv-policies.csv: refresh the measured columns, keep everything else as written
MEAS = re.compile(r'^Measured from the reservation system: longest site \d+ ft; ?')
for r in policies:
    s = state_sum.get(r['State'])
    base = MEAS.sub('', r['Max RV Length'])
    r['Max RV Length'] = (f"Measured from the reservation system: longest site {s['hi']} ft; " + base) if s else base
    r['Measured Avg Site (ft)'] = s['avg'] if s else ''
    r['Measured Longest (ft)'] = s['hi'] if s else ''
    t = state_times.get(r['State'])
    for k in ('Campsite Check-in', 'Campsite Check-out', 'Check-in/out Source'): r.setdefault(k, '')
    if t:
        r['Campsite Check-in'], r['Campsite Check-out'] = t['Check-in'], t['Check-out']
        r['Check-in/out Source'] = t['Source']
with open(P('rv-policies.csv'), 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(policies[0].keys())); w.writeheader(); w.writerows(policies)

tot_sites = sum(s['n'] for s in state_sum.values()); tot_parks = sum(s['parks'] for s in state_sum.values())
fed_sites = sum(s['n'] for s in fed_sum.values()); fed_cgs = sum(s['parks'] for s in fed_sum.values())
n_states = len(state_sum)

# ---------------------------------------------------------------- fit-tool data
STATES = sorted(ABBR.values())
AGS = [''] + list(AGENCY)
fit = []
for p in list(sp.values()) + list(fp.values()):
    flat = []
    for ln, hk, amps, en, n in sorted(p['c']):
        flat += [ln, HK[hk], amps, EN[en], n]
    ci, co = fed_times.get(p['fid'], ('', '')) if p.get('fid') else (st_time(p['state'], 'Check-in'), st_time(p['state'], 'Check-out'))
    fit.append([STATES.index(p['state']), p['name'], AGS.index(p['ag']), p.get('fid', ''), flat, ci, co])
FIT = dict(states=STATES, ags=[AGENCY.get(a, 'State park') for a in AGS], book={STATES.index(k): v for k, v in BOOK.items()}, p=fit)

# ---------------------------------------------------------------- HTML fragments
def a(url, text=None):
    host = re.sub(r'^www\.', '', re.sub(r'^https?://([^/]+).*', r'\1', url))
    return f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(text or host)}</a>'

def cell(v):
    v = (v or '').strip()
    if not v or v.lower().startswith('not stated'): return '<span class="na">Not stated</span>'
    return esc(v)

def pct(a, b): return f'{round(100 * a / b)}%' if b else '&mdash;'

pol_rows = []
for r in policies:
    s = state_sum.get(r['State'])
    meas = f"<strong>{s['avg']} ft</strong> avg &middot; {s['hi']} ft max" if s else '<span class="na">not measured</span>'
    tow = r['Tow Vehicle Counted in Site Length']
    towc = f'<span class="yes">{esc(tow)}</span>' if tow.upper().startswith('YES') else cell(tow)
    pol_rows.append(f'<tr><td class="st">{esc(r["State"])}</td><td>{meas}</td><td>{cell(MEAS.sub("", r["Max RV Length"]))}</td>'
                    f'<td>{towc}</td><td>{cell(r["Vehicles Allowed per Site"])}</td><td>{cell(r["Where Tow / Extra Vehicles Park"])}</td>'
                    f'<td class="tm">{cell(r.get("Campsite Check-in"))}</td><td class="tm">{cell(r.get("Campsite Check-out"))}</td>'
                    f'<td class="src">{a(r["Source"]) if r["Source"].startswith("http") else esc(r["Source"])}</td></tr>')

def sum_rows(summ):
    out = []
    for st, s in summ.items():
        hk = pct(s['elec'], s['n']) if s['hk_known'] else '<span class="na">not published</span>'
        fh = pct(s['full'], s['n']) if s['hk_known'] else '&mdash;'
        pt = pct(s['pull'], s['n']) if s['en_known'] else '<span class="na">not published</span>'
        out.append(f'<tr><td class="st">{esc(st)}</td><td>{fmt(s["parks"])}</td><td>{fmt(s["n"])}</td><td><strong>{s["avg"]} ft</strong></td>'
                   f'<td>{s["hi"]} ft</td>' + ''.join(f'<td>{fmt(x)}</td>' for x in s['b']) +
                   f'<td>{hk}</td><td>{fh}</td><td>{pt}</td></tr>')
    return '\n'.join(out)

pp_rows = '\n'.join(
    f'<tr><td class="st">{esc(r[0])}</td><td>{esc(r[1])}</td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td><td><strong>{r[5]}</strong></td>'
    f'<td>{r[6]}</td>' + ''.join(f'<td>{x}</td>' for x in r[7:12]) + '</tr>' for r in per_park)

va_rows = '\n'.join(
    f'<tr><td class="st">{a(r["Official Website"], r["Park"])}</td><td>{esc(r["Max Site Length (ft)"])} ft</td>'
    f'<td>{esc(r["RV Sites Counted"])}</td><td>{esc(r["Sites by Size (as published)"])}</td></tr>' for r in virginia)
va_sites = sum(int(r['RV Sites Counted']) for r in virginia)

PARKS = [[r['State'], r['Park Name'], r.get('County', ''), r['Official Website']] for r in parks]
SYS = {r['State']: [r['Park System Name'], r['Official Website']] for r in systems}

biggest = max(state_sum.items(), key=lambda kv: kv[1]['n'])
tight = min(state_sum.items(), key=lambda kv: kv[1]['avg'])
roomy = max(state_sum.items(), key=lambda kv: kv[1]['avg'])

tpl = open(P('site-template.html'), encoding='utf-8').read()
out = (tpl
       .replace('{{N_PARKS}}', fmt(len(parks)))
       .replace('{{POLICY_ROWS}}', '\n'.join(pol_rows))
       .replace('{{STATE_SUM_ROWS}}', sum_rows(state_sum))
       .replace('{{FED_SUM_ROWS}}', sum_rows(fed_sum))
       .replace('{{PER_PARK_ROWS}}', pp_rows)
       .replace('{{VA_ROWS}}', va_rows)
       .replace('{{VA_PARKS}}', str(len(virginia))).replace('{{VA_SITES}}', fmt(va_sites))
       .replace('{{TOT_SITES}}', fmt(tot_sites)).replace('{{TOT_PARKS}}', fmt(tot_parks)).replace('{{N_STATES}}', str(n_states))
       .replace('{{FED_SITES}}', fmt(fed_sites)).replace('{{FED_CGS}}', fmt(fed_cgs)).replace('{{FED_STATES}}', str(len(fed_sum)))
       .replace('{{ALL_SITES}}', fmt(tot_sites + fed_sites))
       .replace('{{UPDATED}}', datetime.date.today().strftime('%B %-d, %Y'))
       .replace('{{PARKS_JSON}}', json.dumps(PARKS, ensure_ascii=False, separators=(',', ':')))
       .replace('{{SYS_JSON}}', json.dumps(SYS, ensure_ascii=False, separators=(',', ':')))
       .replace('{{FIT_JSON}}', json.dumps(FIT, ensure_ascii=False, separators=(',', ':'))))
assert '{{' not in out, re.findall(r'\{\{\w+\}\}', out)

# README: regenerate the tables between <!-- name:start --> / <!-- name:end --> markers
def md_table(summ, label):
    rows = [f'| State | {label} | RV sites | Average | Longest | <25 ft | 25–34 | 35–44 | 45–59 | 60+ | Electric | Full hookup | Pull-through |',
            '|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|']
    for st, x in summ.items():
        hk = lambda v: f'{round(100 * v / x["n"])}%' if x['hk_known'] else '—'
        pt = f'{round(100 * x["pull"] / x["n"])}%' if x['en_known'] else '—'
        rows.append(f'| {st} | {fmt(x["parks"])} | {fmt(x["n"])} | {x["avg"]} ft | {x["hi"]} ft | ' + ' | '.join(fmt(v) for v in x['b']) +
                    f' | {hk(x["elec"])} | {hk(x["full"])} | {pt} |')
    return '\n'.join(rows)
readme = open(P('README.md'), encoding='utf-8').read()
for name, body in (('measured', md_table(state_sum, 'Parks')), ('federal', md_table(fed_sum, 'Campgrounds')),
                   ('counts', f'**{fmt(tot_sites)} state-park campsites across {fmt(tot_parks)} parks in {n_states} states**, plus '
                              f'**{fmt(fed_sites)} federal campsites in {fmt(fed_cgs)} campgrounds**')):
    readme = re.sub(rf'(<!-- {name}:start -->).*?(<!-- {name}:end -->)', lambda m: m.group(1) + '\n' + body + '\n' + m.group(2), readme, flags=re.S)
open(P('README.md'), 'w', encoding='utf-8').write(readme)
open(P('index.html'), 'w', encoding='utf-8').write(out)
print(f'index.html {len(out)/1e6:.2f} MB | state parks: {fmt(tot_sites)} sites, {fmt(tot_parks)} parks, {n_states} states | '
      f'federal: {fmt(fed_sites)} sites, {fmt(fed_cgs)} campgrounds | biggest {biggest[0]} {fmt(biggest[1]["n"])} | '
      f'tightest {tight[0]} {tight[1]["avg"]} | roomiest {roomy[0]} {roomy[1]["avg"]}')
