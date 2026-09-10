# State Parks

A searchable, sortable table of **every individual park in all 50 state park systems** — 3,557 parks, forests, historic sites, recreation areas, beaches, and trails, each linked to its page on the state agency's own website.

- **[View the table](https://tim-army.github.io/State-Parks/)** — search across all 50 states, filter to one state, sort any column.
- **[`parks.csv`](parks.csv)** — `State`, `Park Name`, `Official Website` (one row per park).
- **[`state-park-systems.csv`](state-park-systems.csv)** — one row per state: the park system and its main website.
- **[`index.html`](index.html)** — self-contained page; data is embedded, no build step, no dependencies. Two tabs: all parks, and RV rules by state.

## Parks per state

| State | Parks | State | Parks | State | Parks |
|---|--:|---|--:|---|--:|
| Alabama | 22 | Louisiana | 36 | Ohio | 69 |
| Alaska | 97 | Maine | 97 | Oklahoma | 38 |
| Arizona | 33 | Maryland | 63 | Oregon | 197 |
| Arkansas | 54 | Massachusetts | 88 | Pennsylvania | 125 |
| California | 263 | Michigan | 108 | Rhode Island | 15 |
| Colorado | 43 | Minnesota | 66 | South Carolina | 51 |
| Connecticut | 70 | Mississippi | 22 | South Dakota | 57 |
| Delaware | 18 | Missouri | 93 | Tennessee | 67 |
| Florida | 183 | Montana | 46 | Texas | 99 |
| Georgia | 41 | Nebraska | 75 | Utah | 42 |
| Hawaii | 47 | Nevada | 29 | Vermont | 56 |
| Idaho | 24 | New Hampshire | 80 | Virginia | 48 |
| Illinois | 135 | New Jersey | 54 | Washington | 147 |
| Indiana | 28 | New Mexico | 35 | West Virginia | 47 |
| Iowa | 67 | New York | 194 | Wisconsin | 115 |
| Kansas | 29 | North Carolina | 47 | Wyoming | 34 |
| Kentucky | 45 | North Dakota | 18 | | |

## How the data was collected

Each state was scraped from its own park agency's website — sitemaps where they existed,
park-finder listings and JSON APIs otherwise. Park names come from the state's own page
titles or listing text, not from a third-party source. The scrapers live in
[`scrape/`](scrape/): [`lib.py`](scrape/lib.py) holds the shared helpers,
[`titles.sh`](scrape/titles.sh) fetches page titles in parallel, and
[`scrape/out/`](scrape/out/) keeps one CSV per state.

Every URL was requested live. 2,952 returned `200`; the remaining 605 return `403` to
command-line clients (New York, Florida, Massachusetts, Nebraska, Louisiana, and Kansas all
sit behind bot protection) and were verified through a real browser instead. Three dead
Texas URLs were dropped.

Counts reflect what each agency lists today, so a few states include units beyond
"state park" proper — Maine's public lands, New Jersey's state forests and marinas,
Massachusetts's reservations, Wisconsin's state trails — because the agencies list them
alongside their parks.

## RV and tow-vehicle rules

- **[`rv-policies.csv`](rv-policies.csv)** — one row per state: published length limit, measured average and longest site where I could measure it, whether the tow vehicle counts, vehicles per site, where extras park, and a source URL.
- **[`campsite-rv-lengths.csv`](campsite-rv-lengths.csv)** — **23,839 individual campsites across 249 parks in 5 states**, each park summarised: site count, shortest, longest, average, median, and a count of sites in each size band.
- **[`campsite-rv-summary.csv`](campsite-rv-summary.csv)** — the same rolled up per state.
- **[`virginia-rv-site-sizes.csv`](virginia-rv-site-sizes.csv)** — Virginia's own published per-park breakdown (22 parks, 838 sites).
- The **RV rules by state** tab on the [live page](https://tim-army.github.io/State-Parks/) renders all of it.

### Measured site lengths

| State | Parks | RV sites | Average | Longest | <25 ft | 25–34 | 35–44 | 45–59 | 60+ |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Arizona | 15 | 1,444 | 58 ft | 172 ft | 26 | 89 | 236 | 484 | 609 |
| California | 100 | 10,562 | 38 ft | 100 ft | 2,286 | 4,083 | 2,576 | 582 | 1,035 |
| Florida | 64 | 3,293 | 38 ft | 125 ft | 405 | 796 | 1,063 | 795 | 234 |
| Nevada | 18 | 665 | 47 ft | 145 ft | 95 | 73 | 149 | 150 | 198 |
| Ohio | 52 | 7,875 | 44 ft | 130 ft | 170 | 817 | 3,110 | 3,347 | 431 |

California and Florida average 38 ft — and in California nearly a quarter of all sites are under 25 ft. Arizona is the
outlier: 42% of its sites take 60 ft or more.

### How the measurement works

Five states run their reservations on US eDirect / Tyler, whose API exposes a `VehicleLength` on every bookable unit.
[`rv/scrape_usedirect.py`](rv/scrape_usedirect.py) documents the shape; the actual collection ran through a browser
because the API rate-limits scripted clients hard (a 403 after ~90 rapid calls, clearing in about five minutes).

Two corrections matter. Units are deduped by `UnitId`, because the same site is returned by both the park-level and the
loop-level facility. And Ohio is filtered to camping facilities only — its system sells marina dock and mooring
inventory through the same endpoint, with vehicle lengths attached, which inflated the raw count from 7,875 sites to
nearly 17,000. California's "boat-in" facilities are genuine campgrounds and are kept.

### What the states themselves publish

**No state publishes a system-wide maximum RV length.** The limit is set per campsite and lives in the reservation
system — which is exactly why the measured table above exists. Statewide pages give vehicle *counts*, not lengths.

**Does the tow vehicle count?** Four states answer plainly, and all four say yes:

| State | Wording |
|---|---|
| Oregon | "you must also be able to fit your tow vehicle onto the paved driveway" — a 25 ft RV behind a 22 ft vehicle needs a 47 ft site |
| Wisconsin | the listed length "indicates the maximum driveway length you have to fit all your equipment on the site (your trailer or RV, including the tow vehicle)" |
| Arkansas | "combined length … may not exceed the capacity of the camping spur" |
| Missouri | "All wheeled equipment/vehicles must fit on the parking pad/area" |

Florida gets there indirectly ("consider the overall length and width of your camper or RV **and your tow vehicle**"),
and Utah counts them as one unit for vehicle limits. Everywhere else it is unstated — so assume the whole rig has to fit.

**Where the tow vehicle parks** varies: Ohio sends extras to the camp office lot, Pennsylvania to a second-car lot or
onto the spur for a fee, Indiana to designated campground lots, Oregon and Texas to overflow areas. Colorado issues a
free towed-vehicle pass; Arizona waives the extra-vehicle fee for a towed car; Rhode Island's single vehicle pass covers
either the motorhome or the vehicle towing the trailer.

### Limits

Policy rows are sourced from each state agency's own camping rules in September 2026, and every row cites its page.
"Not stated" means the state does not publish that fact, not that no limit exists.

The measured table covers 5 states because only 5 run a reachable US eDirect instance. Texas, Utah, Washington and
Oregon have dead `*rdr.usedirect.com` hostnames — they have migrated to ReserveAmerica, Camis or their own systems,
each of which needs a different scraper. New York, Michigan, Pennsylvania and the rest of ReserveAmerica remain
unmeasured. Georgia, New Mexico and New Hampshire publish RV guides as scanned graphic PDFs that yield no text.

## Updating

Re-run a state's scraper in `scrape/`, then rebuild `parks.csv` and re-embed the data in
`index.html`.
