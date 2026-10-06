# Data sources: what lives where

Checked 2026-10-04 against Forever beta build 1.60.1.70205.

## Talent trees come from the Trait tables, not `Talent`

- The client's legacy `Talent`/`TalentTab` tables are **stale**: they hold an earlier draft of the Forever mage trees (no Hot Streak, Heating Up or Fingers of Frost; Burning Soul at 2 ranks; Flame Throwing and Fire Power still present). wago.tools' hotfix option doesn't change them.
- The live trees are built on the modern **Trait** system: one trait tree per class holds all three trees side by side (mage = trait tree 1112, 54 nodes, matching wowforevertalent.com's 18/17/19).
  - Tree = PosX band (mage: Arcane from 1020, Fire from 5020, Frost from 9080); row/column = PosY/PosX steps of 600 from the first row (PosY 2130).
  - Ranks: `TraitNodeEntry.MaxRanks`; spell: `TraitDefinition.SpellID`; prerequisites: `TraitEdge` (left → right).
  - Per-class layout lives in `src/wowforever/classes/<class>.py`.
- Prerequisite rank is assumed to be the prerequisite's max rank (Classic rule; the legacy table agrees, e.g. Combustion needs Critical Mass 3/3). Not yet confirmed from `TraitCond`.

## Spell data

- Spell tables (`SpellEffect`, `SpellMisc`, `SpellTargetRestrictions`, ...) do carry Forever values: Cone of Cold's slow is 40%, and no AoE spell has a `MaxTargets` cap.

## Source lag

- wowforevertalent.com and wago.tools update independently (on 2026-10-04: 1.60.1.70170 vs 1.60.1.70205). The normalizer reports this; the cross-check (#12) compares contents.

## Community builds

- **wowforevertalent.com popularity** (calculator pages, `data/popularity/<class>.json`): the five most-saved complete builds per class; the community standards in `config/builds/` cite them.
- **wowforevertalent.com build catalog** (`/builds/`): 149 plans (published guides and site plans, not playtested) with final ranks or a point order. `tools/import_wft_builds.py` fills spec-matrix slots that have no popularity standard; plans the site marks "needs review" carry no ranks and are skipped.

## Forever Logs (combat logs)

- [foreverlogs.gg](https://foreverlogs.gg/) publishes an **official public API** at `/api/public/v1` ([docs](https://foreverlogs.gg/docs/api)).
  - `stats:read` (free key from Profile Settings): class and spec DPS statistics by phase, zone and boss; 30 requests/minute, 5,000/day.
  - `events:read` (granted by hand on their Discord): report lists and per-encounter combat events.
  - Send the key as an `X-API-Key` or `Authorization: Bearer` header, never in a URL. Keep it in `.env` as `FOREVERLOGS_API_KEY` (gitignored).
  - Terms: visible attribution wherever its data is shown publicly; no bulk redistribution of the dataset.
- The site's internal `/api/` (used by its own pages) and `/reports/` are disallowed for crawlers in its robots.txt; this project uses only the public API and HAR files a person saved while browsing (`wowforever import-logs`).
- Cached responses live in `data/cache/foreverlogs/` (gitignored). `wowforever validate-logs` compares them with the model (#172).
- During the beta the level cap is 30, so the logs are level 15-30 dungeons; `config/log_levels.toml` maps each dungeon to a typical level.

## wago.tools access

- Published API ([wago.tools](https://wago.tools/), "APIs" page): `/api/builds` (versions per product; `update` uses it to find the latest build), `/api/casc/{fdid}` (a game file by file id), `/api/info/{fdid}` (a file's name and versions) and `/api/files` (the file list per version). `ICON_OVERRIDES` in `classes/warrior.py` were named through `/api/info/{fdid}`.
- **Open question:** the table CSVs `update` downloads (`/db2/<table>/csv?build=...`) are the site's download links, not part of the published API, and wago.tools' robots.txt disallows everything but the home page. Options: confirm with wago.tools (their Discord) that tools may use the CSV exports, or read the same tables from `/api/casc/{fdid}` (raw DB2 files; needs a DB2 parser). Until then, run `update` sparingly; the tables are cached per build in `data/cache/wago/`.
