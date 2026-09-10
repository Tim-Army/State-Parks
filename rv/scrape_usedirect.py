#!/usr/bin/env python3
"""Per-campsite RV lengths from US eDirect (usedirect.com) state reservation APIs.

The API rate-limits bursts with a 403, so requests are serialised with a delay
and exponential backoff. Units are deduped by UnitId because the same site is
returned by both the park-level and loop-level facility.
"""
import json, subprocess, datetime, statistics, csv, time, sys

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')
DELAY = 0.7          # polite gap between calls
MAX_BACKOFF = 300    # give a throttle up to 5 min to clear

STATES = [('Florida','florida'), ('Ohio','ohio'), ('Arizona','az'), ('Nevada','nevada')]

def base(slug):
    return f"https://{slug}rdr.usedirect.com/{slug[0].upper()}{slug[1:]}rdr/rdr/"

def _curl(args):
    return subprocess.run(['curl','-sS','--compressed','--max-time','60','-A',UA]+args,
                          capture_output=True).stdout.decode('utf-8','replace')

def call(url, body=None, tries=7):
    wait = 10
    for _ in range(tries):
        args = [url] if body is None else \
               ['-H','Content-Type: application/json','-X','POST','-d',json.dumps(body),url]
        out = _curl(args)
        time.sleep(DELAY)
        try:
            return json.loads(out)
        except Exception:
            time.sleep(min(wait, MAX_BACKOFF)); wait *= 2
    return None

def scrape(state, slug):
    B = base(slug)
    day = (datetime.date.today()+datetime.timedelta(days=45)).isoformat()
    places = {p['PlaceId']: p['Name'] for p in (call(B+'fd/places') or [])}
    facs = call(B+'fd/facilities') or []
    seen, errs = {}, 0
    for i, f in enumerate(facs, 1):
        j = call(B+'search/grid', {"FacilityId":f['FacilityId'],"StartDate":day,"Nights":"1",
              "UnitSort":"orderby","InSeasonOnly":False,"WebOnly":False,"IsADA":False,
              "UnitCategoryId":0,"SleepingUnitId":0,"MinVehicleLength":0,
              "UnitTypesGroupIds":[],"UnitTypeIds":[]})
        if not j:
            errs += 1
        else:
            for v in ((j.get('Facility') or {}).get('Units') or {}).values():
                uid, ln = v.get('UnitId'), v.get('VehicleLength')
                if uid is not None and isinstance(ln,(int,float)) and ln > 0:
                    seen.setdefault(uid, (f['PlaceId'], ln))
        if i % 50 == 0:
            print(f'  {state}: {i}/{len(facs)} facilities, {len(seen)} sites', flush=True)
    by = {}
    for pid, ln in seen.values():
        by.setdefault(pid, []).append(ln)
    rows = []
    for pid, L in by.items():
        L.sort(); n = len(L)
        rows.append([state, places.get(pid, f'Place {pid}'), n, L[0], L[-1],
                     round(sum(L)/n), int(statistics.median(L)),
                     sum(1 for x in L if x < 25), sum(1 for x in L if 25 <= x < 35),
                     sum(1 for x in L if 35 <= x < 45), sum(1 for x in L if 45 <= x < 60),
                     sum(1 for x in L if x >= 60)])
    rows.sort(key=lambda r: r[1])
    print(f'{state}: {len(rows)} parks, {sum(r[2] for r in rows)} RV sites, {errs} facility errors', flush=True)
    return rows

if __name__ == '__main__':
    out = []
    for state, slug in STATES:
        try:
            out += scrape(state, slug)
        except Exception as e:
            print(f'{state}: FAILED {e}', flush=True)
        with open('usedirect_sites.csv','w',newline='') as fh:
            w = csv.writer(fh)
            w.writerow(['State','Park','RV Sites','Shortest (ft)','Longest (ft)','Average (ft)',
                        'Median (ft)','Under 25 ft','25-34 ft','35-44 ft','45-59 ft','60 ft+'])
            w.writerows(out)
    print('WROTE', len(out), 'rows', flush=True)
