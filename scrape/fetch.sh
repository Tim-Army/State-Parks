#!/bin/bash
# fetch.sh <url> [outfile] -- polite fetch with browser UA
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
curl -sS -L --compressed --max-time 60 -A "$UA" -H 'Accept-Language: en-US,en;q=0.9' "$1" ${2:+-o "$2"}
