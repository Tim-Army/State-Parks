#!/usr/bin/env python3
"""Normalize the per-platform aggregates in rv/sites/*.txt into one table of RV-capable campsites.

Each rv/sites/<st>.txt is written by one of the in-browser scrapers in rv/browser/ and starts with
dictionary lines (T|, E|, A| for ReserveAmerica; T| for US eDirect; C|, S|, M|, E| for GoingToCamp),
followed by one line per park: Park|k1:k2:...:count,...

Output: rv/site-combos.csv  State,Park,Max Length (ft),Hookups,Amps,Entry,Sites
  Hookups: F = full (electric+water+sewer), WE = water+electric, E = electric, N = none, ? = not published
  Amps: highest amp service published for the site (0 = not published / none)
  Entry: P = pull-through, B = back-in, ? = not published
Units that can't take an RV (cabins, yurts, tent-only, hike/bike, boat-in, day use, equestrian, ...) are dropped.
"""
import csv, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
STATES = {'az': 'Arizona', 'ca': 'California', 'de': 'Delaware', 'fl': 'Florida', 'ga': 'Georgia', 'ia': 'Iowa',
          'il': 'Illinois', 'md': 'Maryland', 'mi': 'Michigan', 'mo': 'Missouri', 'mt': 'Montana', 'nc': 'North Carolina',
          'nd': 'North Dakota', 'tn': 'Tennessee', 'sc': 'South Carolina', 'al': 'Alabama', 'ar': 'Arkansas',
          'ky': 'Kentucky', 'in': 'Indiana', 'vt': 'Vermont', 'pa': 'Pennsylvania', 'ok': 'Oklahoma', 'ct': 'Connecticut',
          'nh': 'New Hampshire', 'ri': 'Rhode Island', 'ma': 'Massachusetts', 'ak': 'Alaska', 'mn': 'Minnesota', 'ms': 'Mississippi',
          'co': 'Colorado', 'ks': 'Kansas', 'sd': 'South Dakota', 'la': 'Louisiana', 'wy': 'Wyoming', 'ne': 'Nebraska', 'nm': 'New Mexico', 'nv': 'Nevada', 'ny': 'New York', 'oh': 'Ohio',
          'or': 'Oregon', 'tx': 'Texas', 'ut': 'Utah', 'va': 'Virginia', 'wa': 'Washington', 'wi': 'Wisconsin'}

NOT_RV = re.compile(r'cabin|cottage|yurt|lodge|hotel|dorm|ramada|pavilion|day ?use|picnic|boat|dock|slip|mooring|marina|'
                    r'walk.?in|hike|bike|camp ?host|shelter|lean.?to|tipi|teepee|glamping|platform|parking|launch|finger|'
                    r'transient|balcony|queen|rental|equest|horse|bunkhouse|house|room|hut|adirondack|overflow|'
                    r'floating|off.?road|marine trail|kayak|canoe|paddle|backpack|primitive group|harbor|emergency|backcountry|tiny house|cart.?in|wall tent|beach chair', re.I)
TENT = re.compile(r'\btent\b', re.I)
RVWORD = re.compile(r'\brv\b|trailer|motor ?home|camper|hook.?up|electric|\bfhu\b|sewer', re.I)

def rv_ok(label):
    if NOT_RV.search(label): return False
    if TENT.search(label) and not RVWORD.search(label): return False
    return True

def amps_of(s):
    a = [int(x) for x in re.findall(r'(\d{2,3})\s*(?:/|amp|a\b|,|\s|$)', s or '', re.I) if int(x) in (15, 20, 30, 50, 100)]
    return max(a) if a else 0

def hookups_of(s):
    s = s or ''
    if re.search(r'no (utilities|hook|electric)|non.?electric|without (hook|electric)|standard - no', s, re.I): return 'N'
    full = re.search(r'full.?hook|\bfhu\b|\bews\b|e ?/ ?w ?/ ?s', s, re.I)
    e = full or re.search(r'electric|\(e ?\)|\be ?/|\bew\b|hook.?up|\bamp|\bpower|\b(15|20|30|50) ?a\b', s, re.I)
    w = full or re.search(r'water|/ ?w\b|\bew\b', s, re.I)
    sw = full or re.search(r'sewer|/ ?s\b', s, re.I)
    if e and w and sw: return 'F'
    if e and w: return 'WE'
    if e: return 'E'
    if re.search(r'primitive|rustic|\bdry\b|basic|no services', s, re.I): return 'N'
    return None

def entry_of(s):
    s = s or ''
    if re.search(r'pull|drive.?thr|thru', s, re.I): return 'P'
    if re.search(r'back|head.?in|parallel|straight', s, re.I): return 'B'
    return '?'

def read(path):
    D, parks = {}, []
    for line in open(path, encoding='utf-8'):
        line = line.rstrip('\n')
        if len(line) > 1 and line[1] == '|' and line[0] in 'TEACSMH':
            D[line[0]] = line[2:].split('~')
        elif '|' in line:
            name, body = line.split('|', 1)
            parks.append((name.strip(), [list(map(int, x.split(':'))) for x in body.split(',') if x]))
    return D, parks

# Illinois labels sites by class, not by hookups (17 Ill. Adm. Code 130.70; dnr.illinois.gov/parks/camp.html).
IL_CLASS = [(r'Class AA', 'Electric, Water, Sewer'), (r'Class A\b|Class B.?E', 'Electric'),
            (r'Class B.?S|Class C', 'No electric'), (r'Class D', 'Walk-in')]

def translate(st, label):
    if st == 'il':
        for rx, words in IL_CLASS:
            if re.search(rx, label): return label + ' ' + words
    return label

def rows_for(st, path):
    D, parks = read(path)
    if 'T' in D: D['T'] = [translate(st, t) for t in D['T']]
    kind = 'gtc' if 'C' in D else 'it' if 'H' in D else 'ra' if 'A' in D else 'ud'
    # If this state's own vocabulary names hookups anywhere, a site that doesn't mention them has none.
    vocab = D.get('S', []) + D.get('A', []) + D.get('T', []) + D.get('M', []) + D.get('H', [])
    explicit = any(hookups_of(v) in ('E', 'WE', 'F') for v in vocab)
    for park, combos in parks:
        for k in combos:
            if kind == 'ud':        # len:type:pull:count
                L, t, pt, n = k; label = D['T'][t]; text = label; ent = 'P' if pt else '?'
            elif kind == 'ra':      # len:type:entry:amenities:count
                L, t, e, a, n = k; label = D['T'][t]; text = label + ' ' + D['A'][a]; ent = entry_of(D['E'][e])
            elif kind == 'it':      # len:label:hookups:entry:count (Itinio)
                L, t, hh, e, n = k; label = D['T'][t]; text = label + ' ' + D['H'][hh].replace(';', ', '); ent = entry_of(D['E'][e])
            else:                   # len:category:service:amps:entry:count
                L, c, s, m, e, n = k; label = D['C'][c] + ' ' + D['S'][s]; text = D['S'][s] + ' ' + D['M'][m]; ent = entry_of(D['E'][e])
            if not rv_ok(label) or not (8 <= L <= 200): continue
            hk = hookups_of(text)
            amps = amps_of(text)
            if hk is None: hk = 'E' if amps else 'N' if explicit else '?'
            yield [STATES[st], titlecase(park), L, hk, amps, ent, n]

def titlecase(s):
    if s.isupper() or s.islower():
        s = re.sub(r"[A-Za-z]+('[A-Za-z]+)?", lambda m: m.group(0).capitalize(), s.lower())
        s = re.sub(r'\b(Of|The|And|At|On|In)\b', lambda m: m.group(0).lower(), s)
        s = re.sub(r'\b(Sp|Sra|Shp|Sb|Rv|Ii|Iii)\b', lambda m: m.group(0).upper(), s)
    return s[0].upper() + s[1:] if s else s

if __name__ == '__main__':
    out = collections.Counter()
    for f in sorted(os.listdir(os.path.join(HERE, 'sites'))):
        st = f[:-4]
        if not f.endswith('.txt') or st not in STATES: continue
        for r in rows_for(st, os.path.join(HERE, 'sites', f)):
            out[tuple(r[:6])] += r[6]
    rows = sorted([list(k) + [v] for k, v in out.items()], key=lambda r: (r[0], r[1].lower(), r[2]))
    with open(os.path.join(HERE, 'site-combos.csv'), 'w', newline='') as fh:
        w = csv.writer(fh); w.writerow(['State', 'Park', 'Max Length (ft)', 'Hookups', 'Amps', 'Entry', 'Sites']); w.writerows(rows)
    by = collections.defaultdict(collections.Counter)
    for r in rows: by[r[0]][r[3]] += r[6]; by[r[0]]['_n'] += r[6]; by[r[0]]['_P'] += r[6] if r[5] == 'P' else 0
    for s, c in sorted(by.items()):
        n = c['_n']; print(f"{s:15} {n:6}  F {c['F']/n:4.0%}  WE {c['WE']/n:4.0%}  E {c['E']/n:4.0%}  N {c['N']/n:4.0%}  ? {c['?']/n:4.0%}  pull {c['_P']/n:4.0%}")
