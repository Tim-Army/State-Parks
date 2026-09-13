#!/usr/bin/env python3
"""Park addresses from the state reservation systems, for states whose own websites block scripted requests
or build their pages with JavaScript (Florida, Illinois, Minnesota, Wisconsin, ...).

US eDirect / Tyler: fd/places carries Address1, City, State, Zip per park.
Camis / GoingToCamp:  /api/resourceLocation carries streetAddress + city inside localizedValues
                      (googleAddress is null on these tenants).

Writes <cache>/addr_res.json as {"State|Park name from the reservation system": "address"}; scrape/welcome_centers.py
matches those names to parks.csv.

Usage: python3 scrape/addr_reservations.py <cache-dir>
"""
import json, os, re, ssl, sys, time, urllib.request

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'
UD = {  # state -> fd/places endpoint
    'California': 'https://california-rdr.prod.cali.rd12.recreation-management.tylerapp.com/rdr/fd/places',
    'Florida': 'https://floridardr.usedirect.com/FloridaRDR/rdr/fd/places',
    'Ohio': 'https://ohiordr.usedirect.com/OhioRDR/rdr/fd/places',
    'Arizona': 'https://azrdr.usedirect.com/AzRDR/rdr/fd/places',
    'Nevada': 'https://nevadardr.usedirect.com/NevadaRDR/rdr/fd/places',
    'Missouri': 'https://msprdr.usedirect.com/MSPRDR/rdr/fd/places',
    'North Dakota': 'https://ndparksrdr.usedirect.com/rdr/rdr/fd/places',
    'Virginia': 'https://prod-va-rdr.recreation-management.tylerapp.com/virginiardr/rdr/fd/places',
    'Illinois': 'https://il-rdr.recreation-management.tylerapp.com/IllinoisRDR/rdr/fd/places',
    'Minnesota': 'https://mnrdr.usedirect.com/minnesotardr/rdr/fd/places',
    'Wyoming': 'https://wyordr.usedirect.com/wyomingrdr/rdr/fd/places',
}
GTC = {  # state -> GoingToCamp tenant
    'Washington': 'https://washington.goingtocamp.com/api/resourceLocation',
    'Wisconsin': 'https://wisconsin.goingtocamp.com/api/resourceLocation',
    'Michigan': 'https://midnrreservations.com/api/resourceLocation',
}

def get(url, tries=3):
    for t in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=60, context=ssl._create_unverified_context()) as r:
                return json.load(r)
        except Exception as e:
            if t == tries - 1: print('  fail', url, e, flush=True); return None
            time.sleep(8 * (t + 1))

def clean(s): return re.sub(r'\s+', ' ', (s or '').strip(' ,'))

def title(s):
    s = clean(s)
    return re.sub(r'[A-Za-z]+', lambda m: m.group(0).capitalize(), s) if s.isupper() else s

def main():
    out = {}
    for state, url in UD.items():
        d = get(url) or []
        n = 0
        for p in d:
            a1, city, zp = clean(p.get('Address1')), clean(p.get('City')), clean(p.get('Zip'))
            if not (a1 and city): continue
            addr = f"{title(a1)}, {title(city)}, {state} {zp}".strip()
            out[f"{state}|{clean(p.get('Name'))}"] = addr; n += 1
        print(f'{state}: {n} addresses from {len(d)} places', flush=True)
        time.sleep(1)
    for state, url in GTC.items():
        d = get(url) or []
        n = 0
        for p in d:
            lv = (p.get('localizedValues') or [{}])[0]
            name = clean(lv.get('fullName') or lv.get('shortName'))
            street, city = clean(lv.get('streetAddress')), clean(lv.get('city'))
            addr = clean(p.get('googleAddress')) or (f'{street}, {city}, {state}' if street and city else street or '')
            if not (name and addr and re.search(r'\d', addr)): continue
            out[f'{state}|{name}'] = re.sub(r',?\s*(USA|United States)$', '', addr); n += 1
        print(f'{state}: {n} addresses from {len(d)} locations', flush=True)
        time.sleep(1)
    p = os.path.join(sys.argv[1], 'addr_res.json')
    json.dump(out, open(p, 'w'))
    print('total', len(out), '->', p)

if __name__ == '__main__':
    main()
