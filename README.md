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

- **[`rv-policies.csv`](rv-policies.csv)** — one row per state: maximum RV length, whether the tow vehicle counts toward it, vehicles allowed per site, where extra vehicles park, whether site sizes are published, and the source URL.
- **[`virginia-rv-site-sizes.csv`](virginia-rv-site-sizes.csv)** — Virginia's per-park breakdown: 22 parks, 838 RV sites, counted by size.
- The **RV rules by state** tab on the [live page](https://tim-army.github.io/State-Parks/) renders both.

### What the research found

**No state publishes a single system-wide maximum RV length.** The limit is set per campsite and lives in each
state's reservation system. Statewide pages give vehicle *counts* (usually one camping unit plus one or two
vehicles), not lengths.

**Does the tow vehicle count?** Four states answer plainly, and all four say yes:

| State | Wording |
|---|---|
| Oregon | "you must also be able to fit your tow vehicle onto the paved driveway" — a 25 ft RV behind a 22 ft vehicle needs a 47 ft site |
| Wisconsin | the listed length "indicates the maximum driveway length you have to fit all your equipment on the site (your trailer or RV, including the tow vehicle)" |
| Arkansas | "combined length … may not exceed the capacity of the camping spur" |
| Missouri | "All wheeled equipment/vehicles must fit on the parking pad/area" |

Florida gets there indirectly ("consider the overall length and width of your camper or RV **and your tow
vehicle**"), and Utah counts them as one unit for vehicle limits ("a vehicle and attached in tow equipment is
considered one vehicle"). Everywhere else it is unstated — so assume the whole rig has to fit on the pad.

**Average site length and site-size counts** are only computable where a state publishes per-site data.
Virginia publishes a complete per-park table; Maine classifies every site S/M/L/X/U (to 20/25/30/35/over 35 ft);
Wisconsin buckets sites into 5 ft intervals in its reservation filter. The rest keep it per-site inside the
booking system.

**Where the tow vehicle parks** varies: Ohio sends extras to the camp office lot, Pennsylvania to a second-car
lot or onto the spur for a fee, Indiana to designated campground lots, Oregon and Texas to overflow areas.
Colorado issues a free towed-vehicle pass; Arizona waives the extra-vehicle fee for a towed car; Rhode Island's
single vehicle pass covers either the motorhome or the vehicle towing the trailer.

### Limits of this table

Sourced from each state agency's own camping rules, regulations, and FAQ pages in September 2026 — every row
cites the page it came from. Rows reading "Not stated" mean the state does not publish that fact, not that no
limit exists. Georgia, New Mexico, and New Hampshire each publish an RV guide as a scanned graphic PDF whose
per-park numbers could not be extracted. ReserveCalifornia's API (which also serves Florida, Texas, Utah, Ohio
and Washington) was unreachable during collection, so per-site lengths for those states were not harvested.

## Updating

Re-run a state's scraper in `scrape/`, then rebuild `parks.csv` and re-embed the data in
`index.html`.
