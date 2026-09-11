"""Build federal RV campsite data from the public RIDB full export.
Usage: python3 federal/build_ridb.py <dir-with-unzipped-RIDBFullExport_V1_CSV>
Source: https://ridb.recreation.gov/downloads/RIDBFullExport_V1_CSV.zip (public, refreshed daily)."""
import csv, sys, os, re, collections as C
D = sys.argv[1]
def rd(n): return csv.DictReader(open(os.path.join(D, n + '_API_v1.csv'), encoding='utf-8-sig'))
RIG = {'RV', 'TRAILER', 'FIFTH WHEEL', 'RV/MOTORHOME', 'CARAVAN/CAMPER VAN', 'PICKUP CAMPER', 'POP UP'}
SKIP = re.compile(r'MANAGEMENT|TENT ONLY|WALK TO|HIKE TO|BOAT|CABIN|YURT|SHELTER|PICNIC|MOORING|PARKING|GROUP|EQUESTRIAN|LOOKOUT|ZONE', re.I)
orgs = {r['OrgID']: r['OrgAbbrevName'] or r['OrgName'] for r in rd('Organizations')}
fac_org = {}
for r in rd('OrgEntities'):
    if r['EntityType'] in ('Facility', 'Campground'): fac_org.setdefault(r['EntityID'], orgs.get(r['OrgID'], ''))
fac = {r['FacilityID']: r for r in rd('Facilities')}
state = {}
for r in rd('FacilityAddresses'):
    if r['AddressStateCode'].strip(): state.setdefault(r['FacilityID'], r['AddressStateCode'].strip().upper())
eq = C.defaultdict(float)
for r in rd('PermittedEquipment'):
    if r['EquipmentName'].strip().upper() in RIG:
        try: eq[r['CampsiteID']] = max(eq[r['CampsiteID']], float(r['MaxLength'] or 0))
        except ValueError: pass
at = C.defaultdict(dict)
WANT = {'Max Vehicle Length', 'Driveway Entry', 'Electricity Hookup', 'Water Hookup', 'Sewer Hookup'}
for r in rd('CampsiteAttributes'):
    if r['AttributeName'] in WANT: at[r['EntityID']][r['AttributeName']] = r['AttributeValue'].strip()
def num(s):
    try: return float(s)
    except (ValueError, TypeError): return 0.0
def amps(s):
    n = [int(x) for x in re.findall(r'\d+', s or '') if int(x) in (15, 20, 30, 50, 100)]
    return max(n) if n else 0
def yes(s): return (s or '').strip().lower() in ('y', 'yes', 'water hookup', 'sewer hookup')
def entry(s):
    s = (s or '').lower()
    return 'P' if 'pull' in s else 'B' if 'back' in s else 'L' if 'parallel' in s else ''
def tc(s):
    if not s.isupper(): return s
    s = re.sub(r"[A-Za-z]+('[A-Za-z]+)?", lambda m: m.group(0).capitalize(), s.lower())
    s = re.sub(r'\b(Of|The|And|At|On|In|To)\b', lambda m: m.group(0).lower(), s)
    s = re.sub(r'\b(Rv|Nf|Nra|Sra|Usfs|Blm|Coe|Ii|Iii)\b', lambda m: m.group(0).upper(), s)
    return s[0].upper() + s[1:]
out = []
for r in rd('Campsites'):
    if SKIP.search(r['CampsiteType']): continue
    a = at.get(r['CampsiteID'], {})
    L = eq.get(r['CampsiteID'], 0) or num(a.get('Max Vehicle Length'))
    if not (8 <= L <= 150): continue
    f = fac.get(r['FacilityID'])
    if not f or f['FacilityTypeDescription'] != 'Campground': continue
    st = state.get(r['FacilityID'], '')
    if len(st) != 2: continue
    e = amps(a.get('Electricity Hookup'))
    if not e and 'ELECTRIC' in r['CampsiteType'] and 'NONELECTRIC' not in r['CampsiteType']: e = 1
    out.append([st, fac_org.get(r['FacilityID'], ''), tc(f['FacilityName'].strip()), r['FacilityID'], int(round(L)),
                e, int(yes(a.get('Water Hookup'))), int(yes(a.get('Sewer Hookup'))), entry(a.get('Driveway Entry'))])
def hook(e, w, s):
    return 'F' if e and w and s else 'WE' if e and w else 'E' if e else 'N'
combo = C.Counter()
for st, ag, name, fid, L, e, w, s, ent in out:
    combo[(st, ag, name, fid, L, hook(e, w, s), e if e > 1 else 0, ent or '?')] += 1
rows = sorted([list(k) + [v] for k, v in combo.items()], key=lambda r: (r[0], r[2].lower(), r[4]))
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'federal-combos.csv'), 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['State', 'Agency', 'Campground', 'RIDB Facility ID', 'Max Length (ft)', 'Hookups', 'Amps', 'Entry', 'Sites'])
    w.writerows(rows)
print(sum(r[-1] for r in rows), 'sites', len({r[3] for r in rows}), 'campgrounds', len(rows), 'rows',
      C.Counter(r[1] for r in rows for _ in range(1)).most_common(8))
