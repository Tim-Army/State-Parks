#!/usr/bin/env python3
"""Fill the "Nightly Cost" and "Max Consecutive Nights" columns of parks.csv.

Values are per state park system, from each state's published fee schedule and camping rules
(rv/fees-stay.csv, one row per state with a source). Nightly cost is the range across site types
(tent through full hookup); where a state charges residents and non-residents differently both
ranges are given. Max consecutive nights is the longest single stay the rules allow in one park —
the note column in rv/fees-stay.csv carries the seasonal and per-park exceptions.

Usage: python3 scrape/fees_stay.py
"""
import csv, os, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
COLS = ('Nightly Cost', 'Max Consecutive Nights')

fees = {r['State']: r for r in csv.DictReader(open(os.path.join(ROOT, 'rv', 'fees-stay.csv'), encoding='utf-8'))}

rows = list(csv.DictReader(open(os.path.join(ROOT, 'parks.csv'), encoding='utf-8')))
fields = list(rows[0].keys())
for i, c in enumerate(COLS):
    if c not in fields: fields.insert(fields.index('Separate Tow Parking') + 1 + i, c)
for r in rows:
    f = fees.get(r['State'], {})
    r['Nightly Cost'] = f.get('Nightly Cost', '') or 'Not stated'
    n = f.get('Max Consecutive Nights', '')
    r['Max Consecutive Nights'] = f'{n} nights' if n else 'Not stated'
with open(os.path.join(ROOT, 'parks.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)
print(len(rows), 'parks;', dict(collections.Counter(r['Max Consecutive Nights'] for r in rows)))
