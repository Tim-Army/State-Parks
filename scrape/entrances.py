#!/usr/bin/env python3
"""Fill the "Entrances" column of parks.csv from scrape/entrance-overrides.csv.

No public dataset gives a state park's number of entrances: the agencies don't publish it, Wikidata doesn't
carry it, and OpenStreetMap's entrance tagging is effectively empty for state parks (Oak Mountain, Letchworth
and Custer all return zero entrance nodes). So this column is filled only from verified values recorded in
scrape/entrance-overrides.csv (State, Park Name, Entrances, Source), the same way county overrides work.

Usage: python3 scrape/entrances.py
"""
import csv, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
COL = 'Entrances'

over = {}
p = os.path.join(HERE, 'entrance-overrides.csv')
if os.path.exists(p):
    for r in csv.DictReader(open(p, encoding='utf-8')):
        if r.get('Park Name'): over[(r['State'], r['Park Name'])] = (r.get('Entrances') or '').strip()

rows = list(csv.DictReader(open(os.path.join(ROOT, 'parks.csv'), encoding='utf-8')))
fields = list(rows[0].keys())
if COL not in fields: fields.insert(fields.index('County') + 1, COL)
n = 0
for r in rows:
    v = over.get((r['State'], r['Park Name']), r.get(COL, '') or '')
    r[COL] = v
    if v: n += 1
with open(os.path.join(ROOT, 'parks.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)
print(f'{n} of {len(rows)} parks have an entrance count')
