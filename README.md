# wowforever-helper

Theorycrafting and leveling tools for WoW Forever. Starting with mage (Elementalist: Fire/Frost), built to extend to other classes.

## Progress

Work is tracked in [GitHub issues](https://github.com/alsh0083/wowforever-helper/issues) by [milestone](https://github.com/alsh0083/wowforever-helper/milestones) (`v0` -> `v1` -> `later`). Agent instructions live in `AGENTS.md` / `CLAUDE.md`.

## Contents

- `dashboard/`: offline talent-leveling dashboard (open `dashboard/index.html` in a browser)
- `docs/research/`: Forever mage PvP leveling research report and source notes

## Planned

- Versioned talent data scraped from wowforevertalent.com and Wowhead Forever, with raw snapshots, change logs, and cross-source checks. Update checks run on demand, with no scheduled services.
- Class-agnostic build legality checker and build enumerator
- Deterministic calculator scoring builds on kill power, endurance, survival, and control, then shortlisting by scenario (PvE leveling, world PvP)
- Scenario weights backed by sourced community consensus, recorded as ranges with confidence levels
- Unknown mechanics (e.g. Frostfire Bolt proc interactions) as toggleable assumptions, replaced by dated in-game test results
