# wowforever-helper

Theorycrafting and leveling tools for WoW Forever. Starting with mage (Elementalist: Fire/Frost), built to extend to other classes.

## Progress

Work is tracked in [GitHub issues](https://github.com/alsh0083/wowforever-helper/issues) by [milestone](https://github.com/alsh0083/wowforever-helper/milestones) (`v0` -> `v1` -> `later`). Agent instructions live in `AGENTS.md` / `CLAUDE.md`.

## Setup

```sh
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"   # Windows; use .venv/bin/python elsewhere
.venv/Scripts/python -m pytest
```

## Layout

- `src/wowforever/`: the package (`python -m wowforever`); per-class knowledge lives in `src/wowforever/classes/`, everything else is class-agnostic
- `tests/`: pytest suite; tests use saved fixtures, never the network
- `data/raw/`: immutable source snapshots per game build; normalized datasets alongside
- `config/`: editable assumptions (stat tables, scenario parameters, Frostfire toggles, weights)
- `tools/`: dev tooling such as the local-model Codex wrapper
- `dashboard/`: offline talent-leveling dashboard (open `dashboard/index.html` in a browser)
- `docs/`: research report and notes (`docs/research/`), workflow docs

## Planned

- Versioned talent data scraped from wowforevertalent.com and Wowhead Forever, with raw snapshots, change logs, and cross-source checks. Update checks run on demand, with no scheduled services.
- Class-agnostic build legality checker and build enumerator
- Deterministic calculator scoring builds on kill power, endurance, survival, and control, then shortlisting by scenario (PvE leveling, world PvP)
- Scenario weights backed by sourced community consensus, recorded as ranges with confidence levels
- Unknown mechanics (e.g. Frostfire Bolt proc interactions) as toggleable assumptions, replaced by dated in-game test results

## Data sources and attribution

- Talent trees, rank text and Classic comparisons: [wowforevertalent.com](https://wowforevertalent.com/), licensed under Creative Commons Attribution. Raw page snapshots are kept unmodified under `data/raw/wowforevertalent/`.
- Game data tables: [wago.tools](https://wago.tools/) DB2 exports of the WoW Forever client, per build.
