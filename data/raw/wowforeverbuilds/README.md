# wowforeverbuilds.com snapshots (#460)

One folder per capture date (`YYYYMMDD`). Each holds every class's talent calculator (`talents-<class>.html.gz`),
guide listing (`guides-<class>.html.gz`) and spec guides (`guide-<slug>.html.gz`), gzipped as fetched, plus a
`manifest.json` with the sha256 of the uncompressed pages. Saved by `wowforever.sources.wowforeverbuilds.fetch`;
read back by `load_history`, which `standard_build` uses to read each guide code with the calculator it was made on.

Snapshots are immutable: new data means a new folder.

Source: https://wowforeverbuilds.com/. robots.txt allows these pages. No license is stated, so only facts are used
(decoded build, link, title, date), credited, never the guide text.

- `20261031`: the baseline. The calculators are on beta client 1.60.1.70532 (before the Oct 30 hotfixes). All 54
  guides carry the site-wide `dateModified` 2026-10-24.
