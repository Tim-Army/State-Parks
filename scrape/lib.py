import re, subprocess, sys, os, json, csv, urllib.parse

RAW = os.path.join(os.path.dirname(__file__), 'raw')
OUT = os.path.join(os.path.dirname(__file__), 'out')
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')

def fetch(url, cache=None, force=False):
    """GET url with a browser UA; cache to scrape/raw/<cache>."""
    path = os.path.join(RAW, cache) if cache else None
    if path and os.path.exists(path) and not force and os.path.getsize(path) > 0:
        return open(path, 'rb').read().decode('utf-8', 'replace')
    out = subprocess.run(['curl','-sS','-L','--compressed','--max-time','90','-A',UA,
                          '-H','Accept-Language: en-US,en;q=0.9', url],
                         capture_output=True).stdout
    if path:
        open(path,'wb').write(out)
    return out.decode('utf-8','replace')

def locs(xml):
    return [m.replace('http://','https://') for m in
            re.findall(r'<loc>\s*([^<\s]+)\s*</loc>', xml)]

SMALL = {'of','the','at','and','on','in','a','an','de','du','la','le','for','to','by','at'}
UPPER = {'ohv','rv','atv','wma','nra','shp','sp','usa','ii','iii','iv','vi','vii','viii','ix','xi',
         'nc','sc','nd','sd','wv','ny','pa','ct','ri','nh','nj','dc','tn','ky','mo','ms','al','fl'}
FIX = {'Mcconnells':"McConnell's",'Mcnary':'McNary','Mccormick':'McCormick'}

def titleize(slug):
    s = urllib.parse.unquote(slug).replace('_','-').replace('%20','-')
    s = re.sub(r'\.(html?|aspx|php)$','',s)
    words = [w for w in re.split(r'[-\s]+', s) if w]
    out = []
    for i,w in enumerate(words):
        lw = w.lower()
        if lw in UPPER:
            out.append(w.upper())
        elif lw in SMALL and i not in (0, len(words)-1):
            out.append(lw)
        elif re.match(r"^[a-z]+'[a-z]", w):
            out.append(w[0].upper()+w[1:])
        else:
            out.append(w[:1].upper()+w[1:] if w.islower() or w.istitle() else w)
    t = ' '.join(out)
    t = re.sub(r"\bMc([a-z])", lambda m: 'Mc'+m.group(1).upper(), t)
    t = re.sub(r"\bO'([a-z])", lambda m: "O'"+m.group(1).upper(), t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def clean_name(s):
    s = re.sub(r'<[^>]+>','',s)
    s = (s.replace('&amp;','&').replace('&#039;',"'").replace('&#39;',"'")
          .replace('&rsquo;','’').replace('&nbsp;',' ').replace('&quot;','"')
          .replace('&ndash;','–').replace('&amp;','&'))
    return re.sub(r'\s+',' ',s).strip()

def write(state, rows):
    """rows: list of (name, url) -- dedup by url, sort by name."""
    seen, keep = set(), []
    for n,u in rows:
        n, u = clean_name(n), u.strip()
        if not n or not u or u in seen: continue
        seen.add(u); keep.append((n,u))
    keep.sort(key=lambda r: r[0].lower())
    p = os.path.join(OUT, state.replace(' ','_')+'.csv')
    with open(p,'w',newline='') as f:
        w = csv.writer(f); w.writerow(['State','Park Name','Official Website'])
        for n,u in keep: w.writerow([state,n,u])
    print(f'{state}: {len(keep)} parks -> {p}')
    return keep

def all_locs(state, root, limit=40, filt=None):
    """Download sitemap (index-aware) and cache the loc list at raw/<state>.locs"""
    p = os.path.join(RAW, state+'.locs')
    if os.path.exists(p) and os.path.getsize(p)>0:
        return open(p).read().split()
    xml = fetch(root)
    out = []
    if '<sitemapindex' in xml:
        subs = locs(xml)
        if filt: subs = [s for s in subs if filt in s] or subs
        for s in subs[:limit]:
            out += locs(fetch(s))
    else:
        out += locs(xml)
    out = sorted(set(out))
    open(p,'w').write('\n'.join(out))
    return out

PARKISH = re.compile(r'^[A-Z][^|]{2,70}?\s(State Park|State Park Museum|State Forest|State Beach|State Trail|State Recreation Area|State Recreation Site|State Historic Site|State Historical Site|State Historic Park|State Historical Park|State Natural Area|State Wayside|State Marine Park|State Preserve|State Monument|State Heritage Area|Recreation Area|Wayside|Preserve|Reservoir)$')

def slugify(s):
    return re.sub(r'^-|-$','',re.sub(r'[^a-z0-9]+','-',s.lower()))

def from_names(state, prefix, blob, suffix=''):
    rows=[]
    for line in blob.strip().split('\n'):
        line=line.strip()
        if not line: continue
        n,_,s = line.partition('|')
        rows.append((n, prefix + (s or slugify(n)) + suffix))
    return write(state, rows)
