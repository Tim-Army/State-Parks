#!/usr/bin/env python3
"""Per-site RV lengths from Brandt reservation systems (South Dakota, Louisiana).

Each facility page (FacilityDetails.aspx?facID=N) embeds every unit as JSON in `var sites = [...]` with
MaxEquipLength (999 = no limit set), UnitType ("Back-In Campsite", "Pull-Through Campsite", "Cabin", ...),
OnlineContent ("Amp Service: 20/30/50, ..."), ReservableOnline and IsActive. Facility ids come from
FacilitySearchResults.aspx.

Usage: python3 rv/scrape_brandt.py sd la     -> writes rv/sites/<st>.txt
"""
import collections, html, json, os, re, subprocess, sys, time

HOSTS = {'sd': 'https://reservations.gooutdoorssouthdakota.com', 'la': 'https://reservations.gooutdoorslouisiana.com'}
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'
HERE = os.path.dirname(os.path.abspath(__file__))

def get(url, tries=4):
    for t in range(tries):
        r = subprocess.run(['curl', '-sS', '--compressed', '-L', '--max-time', '120', '-A', UA, url], capture_output=True)
        if r.returncode == 0 and len(r.stdout) > 2000: return r.stdout.decode('utf-8', 'replace')
        time.sleep(15 * (t + 1))
    return ''

def scrape(st):
    base = HOSTS[st]
    s = get(base + '/FacilitySearchResults.aspx')
    ids = sorted({int(x) for x in re.findall(r'"?FacilityID"?\s*[:=]\s*(\d+)', s) + re.findall(r'facID=(\d+)', s)} - {0})
    print(st, len(ids), 'facilities', flush=True)
    out = collections.OrderedDict()
    for fid in ids:
        p = get(f'{base}/FacilityDetails.aspx?facID={fid}&sd=&ed=')
        m = re.search(r'var sites\s*=\s*(\[.*?\]);', p, re.S)
        n = re.search(r"var facilityName\s*=\s*['\"](.*?)['\"];", p)
        name = html.unescape(n.group(1)).strip() if n else f'Facility {fid}'
        if not m: print(f'  {fid} {name}: no site list', flush=True); continue
        units = json.loads(m.group(1))
        rows = []
        for u in units:
            L = u.get('MaxEquipLength') or 0
            if not u.get('ReservableOnline') or not u.get('IsActive', True) or not (0 < L < 999): continue
            rows.append((int(L), (u.get('UnitType') or '').strip(), (u.get('OnlineContent') or '').strip()))
        print(f'  {fid} {name}: {len(units)} units, {len(rows)} with a length', flush=True)
        if rows: out[name] = out.get(name, []) + rows
        time.sleep(2)
    D = {'T': [], 'H': [], 'E': []}
    def ix(d, v):
        if v not in D[d]: D[d].append(v)
        return D[d].index(v)
    lines = []
    for park, rows in out.items():
        c = collections.Counter()
        for L, ut, oc in rows:
            amps = re.search(r'Amp Service:\s*([\d/]+)', oc)
            hook = ';'.join(x for x in [amps.group(1) + ' Amp' if amps else '', 'Water' if re.search(r'\bwater\b', oc, re.I) else '',
                                        'Sewer' if re.search(r'\bsewer\b', oc, re.I) else ''] if x)
            entry = 'Pull-Through' if re.search(r'pull', ut, re.I) else 'Back-In' if re.search(r'back', ut, re.I) else ''
            c[(L, ix('T', ut), ix('H', hook), ix('E', entry))] += 1
        lines.append(park.replace('|', ' ') + '|' + ','.join(':'.join(map(str, k)) + f':{v}' for k, v in c.items()))
    if not out:
        print(st, 'nothing collected - keeping the previous file', flush=True); return
    open(os.path.join(HERE, 'sites', st + '.txt'), 'w').write(
        '\n'.join(['T|' + '~'.join(D['T']), 'H|' + '~'.join(D['H']), 'E|' + '~'.join(D['E'])] + lines))
    print(st, 'parks', len(out), 'sites', sum(len(r) for r in out.values()), flush=True)

if __name__ == '__main__':
    for st in sys.argv[1:] or HOSTS: scrape(st)
