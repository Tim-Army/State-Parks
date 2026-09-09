# State Parks

A searchable, sortable table of the official state park system for all 50 U.S. states.

- **[View the table](https://tim-army.github.io/State-Parks/)** — sortable columns, live search filter.
- **Data:** [`parks.csv`](parks.csv) — `State`, `Park System Name`, `Official Website`.
- **Page:** [`index.html`](index.html) — self-contained; the data is embedded, no build step, no dependencies.

## Scope

For now the table records one row per state: the state's park system and its official website.
All 50 URLs were checked live; a handful of state sites return `403` to command-line clients
but load normally in a browser.

## Updating

Edit `parks.csv`, then mirror the change in the `DATA` array near the bottom of `index.html`.
