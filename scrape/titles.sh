#!/bin/bash
# titles.sh <urlfile>  -> "url<TAB>title" on stdout
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
export UA
one(){
  t=$(curl -sS -L --compressed --max-time 45 -A "$UA" "$1" \
      | tr '\n' ' ' \
      | grep -oiE '<meta[^>]+property="og:title"[^>]*>|<title[^>]*>[^<]*</title>' \
      | head -2 | tail -1)
  t=$(printf '%s' "$t" | sed -E 's/.*content="([^"]*)".*/\1/; s/<title[^>]*>//I; s/<\/title>//I')
  printf '%s\t%s\n' "$1" "$t"
}
export -f one
xargs -P 8 -I{} bash -c 'one "$@"' _ {} < "$1"
