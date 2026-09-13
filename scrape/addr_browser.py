#!/usr/bin/env python3
"""Merge addresses collected through the browser into the address cache.

Some state park sites answer 403 to scripted requests (New York, Massachusetts, Florida, Nebraska, Arkansas),
so those states are crawled from inside a browser tab with the same pattern used by scrape/addresses.py
(see rv/browser/ for the equivalent technique on reservation systems). Each dump file is:

    <State name>
    /path/of/park/page|123 Main St, Town, ST 12345
    ...

The same layout under <cache-dir>/vc/ carries the visitor-center answers (path|Yes or path|No).

Usage: python3 scrape/addr_browser.py <cache-dir>      # reads <cache-dir>/browser/*.txt and <cache-dir>/vc/*.txt
"""
import csv, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

def main():
    cache_dir = sys.argv[1]
    bdir = os.path.join(cache_dir, 'browser')
    rows = list(csv.DictReader(open(os.path.join(ROOT, 'parks.csv'), encoding='utf-8')))
    by_state_path = {}
    for r in rows:
        u = r['Official Website']
        path = '/' + u.split('/', 3)[3] if u.count('/') > 2 else '/'
        by_state_path[(r['State'], path.rstrip('/'))] = u
    cp = os.path.join(cache_dir, 'addr.json')
    cache = json.load(open(cp)) if os.path.exists(cp) else {}
    def dumps(d):
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if not f.endswith('.txt'): continue
            lines = open(os.path.join(d, f), encoding='utf-8').read().splitlines()
            if lines: yield f, lines[0].strip(), lines[1:]

    added = 0
    for f in sorted(os.listdir(bdir)):
        if not f.endswith('.txt'): continue
        lines = open(os.path.join(bdir, f), encoding='utf-8').read().splitlines()
        if not lines: continue
        state = lines[0].strip()
        for line in lines[1:]:
            if '|' not in line: continue
            path, addr = line.split('|', 1)
            url = by_state_path.get((state, path.strip().rstrip('/')))
            if not url or not addr.strip(): continue
            cache[url] = [addr.strip(), 'browser', [addr.strip()]]
            added += 1
        print(f'{f}: {state}')
    vcn = 0
    for f, state, lines in dumps(os.path.join(cache_dir, 'vc')):
        for line in lines:
            if '|' not in line: continue
            path, v = line.split('|', 1); v = v.strip()
            url = by_state_path.get((state, path.strip().rstrip('/')))
            if not url or v not in ('Yes', 'No'): continue
            e = cache.get(url) or ['', 'browser', []]
            while len(e) < 4: e.append('')
            e[3] = v; cache[url] = e; vcn += 1
    json.dump(cache, open(cp, 'w'))
    print('merged', added, 'addresses and', vcn, 'visitor-center answers from the browser dumps')

if __name__ == '__main__':
    main()
