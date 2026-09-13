#!/usr/bin/env python3
"""Collect each park's published physical address (its welcome center / park office) from its own website.

Extraction order per page:
  1. schema.org PostalAddress in JSON-LD or microdata
  2. an explicit "Visitor Center" / "Welcome Center" address block
  3. the first US street address in the page text (street, city, two-letter state, ZIP)
Results are cached per URL in <cache>/addr.json so re-runs are cheap and resumable.

Usage: python3 scrape/addresses.py <cache-dir> [--limit N] [--state "Ohio"]
"""
import csv, html, json, os, re, sys, time, urllib.request, collections, concurrent.futures as cf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'
ST = ('AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY')
# Anchored on ", City, ST ZIP" rather than a street-type word: many parks use formats like
# "2373 ASP, Rte 1, Suite 3, Salamanca, NY 14779" that no Street/Ave/Rd list would catch.
# Anchored on ", ST ZIP" rather than a street-type word: parks use formats like
# "2373 ASP, Rte 1, Suite 3, Salamanca, NY 14779" that no Street/Ave/Rd list would catch.
STREET = re.compile(r"(?<![\d-])(\d{1,6}[A-Za-z]?\s+[A-Za-z0-9 .,'&/#-]{4,70}?),?\s+(" + ST + r")\s+(\d{5})(?:-\d{4})?\b")
CENTER = re.compile(r'(visitor|welcome|nature|interpretive|education|discovery)\s+(center|centre)', re.I)
# "has a visitor center" is only credible as a real mention, not a nav link or a link to another park's center
VC_NEG = re.compile(r'(no|without|closed permanently)\s+(visitor|welcome|nature)\s+(center|centre)', re.I)
STRIP = re.compile(r'<(script|style|noscript)[\s\S]*?</\1>', re.I)

def text_of(h):
    t = html.unescape(re.sub(r'<[^>]+>', ' ', STRIP.sub(' ', h)))
    return re.sub(r'[ \s]+', ' ', t)

def fmt(m):
    body, st, zp = m.groups()
    body = re.sub(r'\s+', ' ', body).strip(' ,.')
    return f'{body}, {st} {zp}'

def from_schema(h):
    for m in re.finditer(r'<script[^>]+application/ld\+json[^>]*>([\s\S]*?)</script>', h, re.I):
        try: data = json.loads(m.group(1).strip())
        except Exception: continue
        stack = [data]
        while stack:
            o = stack.pop()
            if isinstance(o, list): stack += o
            elif isinstance(o, dict):
                a = o.get('address')
                if isinstance(a, dict) and a.get('streetAddress'):
                    parts = [a.get('streetAddress'), a.get('addressLocality'), ' '.join(x for x in (a.get('addressRegion'), a.get('postalCode')) if x)]
                    s = ', '.join(x.strip() for x in parts if x and x.strip())
                    if re.search(r'\d', s): return re.sub(r'\s+', ' ', s)
                stack += [v for v in o.values() if isinstance(v, (dict, list))]
    return ''

VC_CTX = re.compile(r'\b(open|hours|exhibit|gift shop|museum|staff|located|houses|features|displays|aquarium|theater|closed|admission|restrooms)\b', re.I)

def has_center(h):
    """A bare "Welcome Centers" link in site navigation appears on every page of some sites (arkansas.com),
    so a mention only counts when it sits near words describing a real facility, or repeats several times."""
    t = text_of(h)
    if VC_NEG.search(t): return 'No'
    hits = list(CENTER.finditer(t))
    if not hits: return 'No'
    for m in hits:
        if VC_CTX.search(t[max(0, m.start() - 160):m.end() + 200]): return 'Yes'
    return 'Yes' if len(hits) >= 3 else 'No'

def extract(h):
    """Return (best, how, candidates). Several candidates are kept because the first address on a page is
    often the agency's own headquarters (every Texas park page leads with TPWD in Austin)."""
    cands, sch = [], from_schema(h)
    if sch: cands.append(sch)
    t = text_of(h)
    hits = list(STREET.finditer(t))
    near = [fmt(m) for m in hits if CENTER.search(t[max(0, m.start() - 220):m.end() + 120])]
    for a in near + [fmt(m) for m in hits]:
        if a not in cands: cands.append(a)
    if not cands: return '', '', []
    how = 'schema' if sch else ('center' if near else 'page')
    return cands[0], how, cands[:6]

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9'})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read()[:1500000].decode('utf-8', 'replace')

ABBR = {'Alabama':'AL','Alaska':'AK','Arizona':'AZ','Arkansas':'AR','California':'CA','Colorado':'CO','Connecticut':'CT','Delaware':'DE','Florida':'FL','Georgia':'GA','Hawaii':'HI','Idaho':'ID','Illinois':'IL','Indiana':'IN','Iowa':'IA','Kansas':'KS','Kentucky':'KY','Louisiana':'LA','Maine':'ME','Maryland':'MD','Massachusetts':'MA','Michigan':'MI','Minnesota':'MN','Mississippi':'MS','Missouri':'MO','Montana':'MT','Nebraska':'NE','Nevada':'NV','New Hampshire':'NH','New Jersey':'NJ','New Mexico':'NM','New York':'NY','North Carolina':'NC','North Dakota':'ND','Ohio':'OH','Oklahoma':'OK','Oregon':'OR','Pennsylvania':'PA','Rhode Island':'RI','South Carolina':'SC','South Dakota':'SD','Tennessee':'TN','Texas':'TX','Utah':'UT','Vermont':'VT','Virginia':'VA','Washington':'WA','West Virginia':'WV','Wisconsin':'WI','Wyoming':'WY'}

KEY = re.compile(r'.*\b(Location|Address|Directions|Office|Mailing|Contact|SVG)\b[:\s]*', re.I)

BAD = re.compile(r'\b[NSWE]\s*\d|\d+\.\d|\bN\b.*\bW\b|latitude|longitude|^\d+\s*(mi|km|ft|acres)\b', re.I)

def plausible(a):
    """Reject coordinate strings ("30 2.10, W 83 1.14 Mayo, FL 32066"), distances and other numeric noise
    that the anchored pattern can pick up."""
    body = a.rsplit(',', 1)[0]
    if BAD.search(body): return False
    words = [w for w in re.split(r'[\s,]+', body) if w]
    return len(words) >= 3 and sum(c.isalpha() for c in body) >= 6

def tidy(a):
    """Trim page furniture that the anchored pattern can swallow, e.g.
    "5 per vehicle See all fees Location 14326 S. County Road 39 Lithia, FL 33547"."""
    a = KEY.sub('', a).strip(' ,.')
    a = re.sub(r'^(?:[A-Za-z][\w.&-]*\s+){0,4}?(?=\d{1,6}[A-Za-z]?\s)', '', a, count=1)  # drop words before the street number
    return re.sub(r'\s+', ' ', a).strip(' ,.')

def usable(rows, cache):
    """Drop boilerplate: an address repeated across many parks in a state is the agency's own headquarters
    (Texas returned "4200 Smith School Rd, Austin" for every park), and the address must sit in the park's state."""
    def cands(r):
        v = cache.get(r['Official Website']) or []
        return [t for t in (tidy(a) for a in (v[2] if len(v) > 2 and v[2] else ([v[0]] if v and v[0] else []))) if plausible(t)]
    seen = collections.Counter()
    for r in rows:
        for a in cands(r): seen[(r['State'], a)] += 1
    out = {}
    for r in rows:
        for a in cands(r):
            if seen[(r['State'], a)] > 2: continue                  # agency HQ / template address
            m = re.search(r',\s*(' + ST + r')\s+\d{5}', a)
            if m and ABBR.get(r['State']) and m.group(1) != ABBR[r['State']]: continue
            out[(r['State'], r['Park Name'])] = a
            break
    return out

def main():
    cache_dir = sys.argv[1]
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else None
    only = sys.argv[sys.argv.index('--state') + 1] if '--state' in sys.argv else None
    cp = os.path.join(cache_dir, 'addr.json')
    cache = json.load(open(cp)) if os.path.exists(cp) else {}
    rows = list(csv.DictReader(open(os.path.join(ROOT, 'parks.csv'), encoding='utf-8')))
    todo = [r for r in rows if r['Official Website'] not in cache and (not only or r['State'] == only)]
    if limit: todo = todo[:limit]
    last = collections.defaultdict(float)             # one request per host per second
    lock = __import__('threading').Lock()
    def work(r):
        host = r['Official Website'].split('/')[2]
        with lock:
            wait = max(0.0, last[host] + 1.0 - time.time()); last[host] = time.time() + wait
        time.sleep(wait)
        try:
            h = fetch(r['Official Website'])
            addr, how, cands = extract(h)
            vc = has_center(h)
        except Exception as e: return r['Official Website'], ['', 'err:' + type(e).__name__, [], '']
        return r['Official Website'], [addr, how, cands, vc]
    done = 0
    with cf.ThreadPoolExecutor(8) as ex:
        for url, v in ex.map(work, todo):
            cache[url] = v; done += 1
            if done % 50 == 0:
                json.dump(cache, open(cp, 'w')); print(done, 'of', len(todo), flush=True)
    json.dump(cache, open(cp, 'w'))
    good = usable(rows, cache)
    raw = sum(1 for r in rows if (cache.get(r['Official Website']) or [''])[0])
    print(f'{len(good)} of {len(rows)} parks have a usable address ({raw} raw before boilerplate/state checks)',
          collections.Counter((cache.get(r['Official Website']) or ['', '?'])[1] for r in rows).most_common())

if __name__ == '__main__':
    main()
