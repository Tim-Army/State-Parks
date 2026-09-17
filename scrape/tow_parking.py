#!/usr/bin/env python3
"""Fill the "Separate Tow Parking" column of parks.csv.

Values come from each state's published camping rules (rv/tow-parking.csv, summarised from rv-policies.csv):
  Yes                    extra / tow vehicles have a designated lot or overflow area
  Some parks             only some campgrounds offer it
  No, must fit on site   the rules require the tow vehicle to fit on the campsite pad
  Not stated             the state doesn't say (35 states)
Per-park exceptions in scrape/tow-parking-overrides.csv (State, Park Name, Separate Tow Parking, Source) win.

Usage: python3 scrape/tow_parking.py
"""
import csv, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
COL = 'Separate Tow Parking'

state = {r['State']: r[COL] for r in csv.DictReader(open(os.path.join(ROOT, 'rv', 'tow-parking.csv'), encoding='utf-8'))}
over = {(r['State'], r['Park Name']): r[COL] for r in csv.DictReader(open(os.path.join(HERE, 'tow-parking-overrides.csv'), encoding='utf-8')) if r.get('Park Name')}

rows = list(csv.DictReader(open(os.path.join(ROOT, 'parks.csv'), encoding='utf-8')))
fields = list(rows[0].keys())
if COL not in fields: fields.insert(fields.index('Visitor Center?') + 1, COL)
for r in rows:
    r[COL] = over.get((r['State'], r['Park Name'])) or state.get(r['State'], 'Not stated')
with open(os.path.join(ROOT, 'parks.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)
from collections import Counter
print(dict(Counter(r[COL] for r in rows)))
