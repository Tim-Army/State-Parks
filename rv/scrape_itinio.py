#!/usr/bin/env python3
"""Per-site RV lengths from Itinio reservation systems (Tennessee, South Carolina, Alabama, Arkansas).

Itinio has no JSON API, but one form POST per park returns a calendar grid whose site cells carry
data-maxrv (max RV length), data-drivelength, data-access (Pull Through / Back In), data-electric,
data-water and data-sewer. Flow per park: GET /<slug>/camping (or /campsites) for the session cookie,
csrfToken and parkid, then POST the same URL with stage=1&view=parkwide.

Usage: python3 rv/scrape_itinio.py tn sc al ar     -> writes rv/sites/<st>.txt
"""
import datetime, html, http.cookiejar, os, re, sys, time, urllib.parse, urllib.request, collections

HOSTS = {'tn': 'https://reserve.tnstateparks.com', 'sc': 'https://reserve.southcarolinaparks.com',
         'al': 'https://reserve.alapark.com', 'ar': 'https://reserve.arkansasstateparks.com'}
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'
SKIP = {'guest', 'account', 'cart', 'login', 'logout', 'search', 'help', 'faq', 'contact', 'privacy', 'terms', 'gallery',
        'register', 'checkout', 'reservations', 'gift-cards', 'giftcards', 'about', 'home', 'map', 'maps', 'lodging', 'events'}
CSV_STATE = {'ar': 'Arkansas'}
HERE = os.path.dirname(os.path.abspath(__file__))

def opener():
    jar = http.cookiejar.CookieJar()
    o = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    o.addheaders = [('User-Agent', UA), ('Accept-Language', 'en-US,en;q=0.9')]
    return o

def get(o, url, data=None, ref=None, tries=4):
    for t in range(tries):
        try:
            req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode() if data else None)
            if ref: req.add_header('Referer', ref)
            with o.open(req, timeout=60) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception as e:
            if t == tries - 1: print('   fail', url, e, flush=True); return ''
            time.sleep(10 * (t + 1))

def attrs(tag):
    return {k: html.unescape(v) for k, v in re.findall(r'data-([a-z0-9]+)="([^"]*)"', tag)}

def scrape(st):
    base = HOSTS[st]; o = opener()
    home = get(o, base + '/')
    slugs = []
    for s in re.findall(r'href="(?:' + re.escape(base) + r')?/([a-z0-9][a-z0-9-]+)(?:/(?:camping|campsites))?/?"', home):
        if s not in SKIP and s not in slugs: slugs.append(s)
    for s in re.findall(r'<option value="([a-z0-9][a-z0-9-]+)"', home):      # South Carolina: park picker
        if s not in SKIP and s not in slugs: slugs.append(s)
    if st in CSV_STATE:                                                         # Arkansas: no park list at all
        import csv
        for r in csv.DictReader(open(os.path.join(HERE, '..', 'parks.csv'))):
            if r['State'] != CSV_STATE[st]: continue
            s = r['Official Website'].rstrip('/').rsplit('/', 1)[-1]
            for c in (re.sub(r'-state-park$', '', s), s):
                if c not in slugs: slugs.append(c)
    d1 = datetime.date.today() + datetime.timedelta(days=40)
    while d1.weekday() != 1: d1 += datetime.timedelta(days=1)          # a Tuesday: fewest blocked nights
    d2 = d1 + datetime.timedelta(days=2)
    out = collections.OrderedDict()
    for slug in slugs:
        for sub in ('camping', 'campsites'):
            url = f'{base}/{slug}/{sub}'
            p = get(o, url)
            tok = re.search(r'name="csrfToken"[^>]*value="([^"]*)"', p)
            pid = re.search(r'name="parkid"[^>]*value="([^"]*)"', p)
            if tok and pid: break
        else:
            continue
        name = re.search(r'<title>\s*([^<|–-]+)', p)
        name = html.unescape(name.group(1)).strip() if name else slug.replace('-', ' ').title()
        time.sleep(1)
        g = get(o, url, dict(csrfToken=tok.group(1), stage='1', view='parkwide', processing='true', startOver='false',
                             reserve='false', checkin=d1.strftime('%m/%d/%Y'), checkout=d2.strftime('%m/%d/%Y'),
                             parkid=pid.group(1)), ref=url)
        seen = {}
        for tag in re.findall(r'<t[dr]\b[^>]*data-maxrv=[^>]*>', g):      # TN/SC/AL: <td data-site>, AR: <tr data-description>
            a = attrs(tag)
            key = (a.get('description') or a.get('site') or '').strip()
            if not key or key in seen: continue
            L = next((int(a[k]) for k in ('maxrv', 'drivelength', 'parklength') if re.fullmatch(r'\d+', a.get(k, '') or '') and int(a[k]) > 0), 0)
            seen[key] = (L, a)
        rows = [(L, a) for L, a in seen.values() if L > 0]
        print(f'{st} {slug}: {len(seen)} sites, {len(rows)} with a length', flush=True)
        if rows: out[name] = rows
        time.sleep(1)
    # compact format shared with the browser scrapers: dictionaries, then Park|len:label:hook:entry:count
    D = {'T': [], 'H': [], 'E': []}
    def ix(d, v):
        if v not in D[d]: D[d].append(v)
        return D[d].index(v)
    lines = []
    for park, rows in out.items():
        c = collections.Counter()
        for L, a in rows:
            label = re.sub(r'\d+[A-Z]?\b', '', a.get('site') or a.get('description', '')).strip(' -#')
            yes = lambda k: (a.get(k) or '').lower() in ('yes', 'true')
            amp = a.get('electric', '') if a.get('electric', '') not in ('', 'false', 'No', 'None') else ''
            hook = ';'.join(x for x in [amp and (amp if 'amp' in amp.lower() else amp + ' Amp'), 'Water' if yes('water') else '', 'Sewer' if yes('sewer') else ''] if x)
            c[(L, ix('T', label), ix('H', hook), ix('E', a.get('access', '')))] += 1
        lines.append(park.replace('|', ' ') + '|' + ','.join(':'.join(map(str, k)) + f':{v}' for k, v in c.items()))
    if not out:
        print(st, 'nothing collected - keeping the previous file', flush=True); return
    text = '\n'.join(['T|' + '~'.join(D['T']), 'H|' + '~'.join(D['H']), 'E|' + '~'.join(D['E'])] + lines)
    open(os.path.join(HERE, 'sites', st + '.txt'), 'w').write(text)
    print(st, 'parks', len(out), 'sites', sum(len(r) for r in out.values()), flush=True)

if __name__ == '__main__':
    for st in sys.argv[1:] or HOSTS: scrape(st)
