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
- **[`campsite-rv-lengths.csv`](campsite-rv-lengths.csv)** — **92,141 individual campsites across 1,032 parks in 24 states**, each park summarised: site count, shortest, longest, average, median, and a count of sites in each size band.
- **[`campsite-rv-summary.csv`](campsite-rv-summary.csv)** — the same rolled up per state.
- **[`virginia-rv-site-sizes.csv`](virginia-rv-site-sizes.csv)** — Virginia's own published per-park breakdown (22 parks, 838 sites).
- The **RV rules by state** tab on the [live page](https://tim-army.github.io/State-Parks/) renders all of it.

### Measured site lengths

| State | Parks | RV sites | Average | Longest | <25 ft | 25–34 | 35–44 | 45–59 | 60+ |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Arizona | 15 | 1,444 | 58 ft | 172 ft | 26 | 89 | 236 | 484 | 609 |
| California | 100 | 10,562 | 38 ft | 100 ft | 2,286 | 4,083 | 2,576 | 582 | 1,035 |
| Delaware | 5 | 707 | 36 ft | 128 ft | 156 | 84 | 315 | 141 | 11 |
| Florida | 64 | 3,293 | 38 ft | 125 ft | 405 | 796 | 1,063 | 795 | 234 |
| Georgia | 34 | 1,659 | 45 ft | 180 ft | 99 | 247 | 494 | 622 | 197 |
| Illinois | 62 | 6,319 | 41 ft | 221 ft | 593 | 432 | 3,183 | 1,824 | 287 |
| Iowa | 49 | 3,356 | 52 ft | 200 ft | 211 | 455 | 558 | 966 | 1,166 |
| Maryland | 21 | 1,484 | 31 ft | 76 ft | 371 | 736 | 241 | 101 | 35 |
| Michigan | 96 | 12,130 | 47 ft | 200 ft | 241 | 1,295 | 3,584 | 4,972 | 2,038 |
| Missouri | 41 | 3,651 | 55 ft | 173 ft | 93 | 73 | 326 | 2,198 | 961 |
| Montana | 16 | 498 | 36 ft | 85 ft | 97 | 143 | 143 | 86 | 29 |
| Nebraska | 31 | 2,140 | 51 ft | 110 ft | 18 | 28 | 407 | 1,098 | 589 |
| Nevada | 18 | 665 | 47 ft | 145 ft | 95 | 73 | 149 | 150 | 198 |
| New Mexico | 27 | 1,461 | 40 ft | 181 ft | 146 | 407 | 473 | 343 | 92 |
| New York | 99 | 10,138 | 31 ft | 426 ft | 2,798 | 3,858 | 2,498 | 960 | 24 |
| North Carolina | 20 | 860 | 53 ft | 146 ft | 66 | 124 | 122 | 175 | 373 |
| North Dakota | 13 | 1,282 | 58 ft | 225 ft | 80 | 84 | 191 | 435 | 492 |
| Ohio | 52 | 7,875 | 44 ft | 130 ft | 170 | 817 | 3,110 | 3,347 | 431 |
| Oregon | 40 | 5,110 | 41 ft | 135 ft | 521 | 1,018 | 1,522 | 1,640 | 409 |
| Texas | 72 | 4,904 | 48 ft | 223 ft | 639 | 581 | 534 | 2,233 | 917 |
| Utah | 30 | 1,643 | 52 ft | 250 ft | 126 | 294 | 375 | 297 | 551 |
| Virginia | 24 | 1,350 | 41 ft | 183 ft | 263 | 261 | 340 | 298 | 188 |
| Washington | 59 | 4,173 | 43 ft | 147 ft | 600 | 727 | 870 | 1,333 | 643 |
| Wisconsin | 44 | 5,437 | 50 ft | 200 ft | 161 | 680 | 1,090 | 1,913 | 1,593 |

**The two tightest systems are New York and Maryland, both averaging 31 ft** — in New York more than a third of
10,138 sites are under 25 ft, and Maryland has only one site in the whole state over 60 ft. The roomiest are Arizona
and North Dakota at 58 ft. Michigan is the biggest single system measured: 12,130 sites across 96 parks.
(New York's 426 ft "longest" is one bad record at Fair Haven Beach; its real ceiling is 65 ft.)

### How the measurement works

Four platforms run state-park reservations, and each needed its own scraper. All were driven through a browser,
because every one of them rate-limits scripted clients.

**US eDirect / Tyler** — California, Florida, Ohio, Arizona, Nevada, Virginia, Illinois, Missouri, North Dakota.
A JSON API with a `VehicleLength` on every bookable unit; see [`rv/scrape_usedirect.py`](rv/scrape_usedirect.py).
Units are deduped by `UnitId`, because the same site comes back from both the park-level and loop-level facility.
Ohio is filtered to camping facilities only — its system sells marina dock and mooring inventory through the same
endpoint with vehicle lengths attached, which inflated the raw count from 7,875 sites to nearly 17,000.

**ReserveAmerica** — New York, Texas, Iowa, Georgia, Oregon, Utah, Nebraska, New Mexico, Maryland, North Carolina,
Montana, Delaware. No JSON API: each campground's site list is server-rendered HTML with an "Equip length / Driveway"
column, paged 25 at a time through `campsitePaging.do`. Two traps. The pager silently repeats the last page instead
of returning empty, so pages are deduped by site ID and the loop stops when a page adds nothing new — without that,
Georgia's High Falls reported 1,300 sites instead of 87. And the max-people cell can contain an accessibility icon,
which breaks a naive column regex and silently drops every ADA site; that one cost a full New York re-run (6,055
sites on the first pass, 10,138 on the corrected one).

**Camis / GoingToCamp** — Washington, Wisconsin, Michigan. A clean REST API: `/api/resourceLocation` lists parks and
`/api/resourcelocation/resources?resourceLocationId=` returns every site with a `definedAttributes` array. The catch
is that the length attribute is tenant-specific and has to be looked up per state from `/api/attribute/filterable`:
Washington uses "Pad Length" (−32715), Wisconsin "Max Driveway Length" (−32714), Michigan "Site Length" (−32746).
Wisconsin's field is literally the one its FAQ describes as including the tow vehicle.

Spot-checked against published counts: Anastasia 139 (Florida says 139), Topsail Hill 155 (156), Fort Yargo 46 (47),
Skidaway Island 85 (87), Fort Stevens 509 (~470), Deception Pass 311 (~310).

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

The measured table covers the 24 states whose reservation backends expose a per-site length. The rest do not, or run
on bespoke platforms: Tennessee, South Carolina, Alabama, Arkansas, Kentucky, Minnesota, Indiana, New Jersey, Maine
and Vermont each run their own system, and Mississippi is on GoingToCamp but publishes no length attribute at all.
Hawaii has no RV camping in its state park system. Alaska, Colorado, Connecticut, Idaho, Kansas, Louisiana,
Massachusetts, New Hampshire, Oklahoma, Pennsylvania, Rhode Island, South Dakota, West Virginia and Wyoming were
either unreachable or not on a platform with an exposed length field.

Every platform rate-limits hard — US eDirect returns 403 after roughly 90 rapid calls and clears in about five
minutes — so collection ran in throttled bursts with progress checkpointed to `localStorage`, which saved the run
more than once when a page reloaded mid-scrape.

## Updating

Re-run a state's scraper in `scrape/`, then rebuild `parks.csv` and re-embed the data in
`index.html`.
