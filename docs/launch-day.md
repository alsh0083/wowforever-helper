# Launch day and the week after (#376, #308, #424, #438, #450)

WoW Forever launches on 4 November 2026. These checks need the live game or post-launch data, so they wait until
the owner asks. Each one says where its result goes. The patch steps themselves are in `docs/patch-update.md`.

## 1. New build or hotfixes (owner asks)
- Log in to character select once, then copy the client's hotfix cache read-only into
  `data/raw/hotfixes/<build>-<YYYYMMDD>/` with a manifest. See the 3 Nov snapshot's for the fields (#456).
- `.venv/Scripts/python -m wowforever update --hotfixes data/raw/hotfixes/<build>-<date> --rank-text wowforevertalents`.
  If wowforevertalents.com serves no page for a one-rank talent, its rank text comes from the client tooltip (#466).
- `wowforever patch-readiness --dataset data/datasets/<build>.json --tables data/cache/hotfixed/<build>-<date>`, then
  the steps in `docs/patch-update.md`.

## 2. Community standards as the sources settle (#460)
Guides move to the new calculators, and talentsforever.com's window collects saves. Rerun:

    .venv/Scripts/python tools/import_sourced_builds.py
    .venv/Scripts/python tools/seed_tree_builds.py
    (every class report)
    .venv/Scripts/python tools/derive_slot_builds.py
    (every class report)
    .venv/Scripts/python tools/derive_model_picks.py
    .venv/Scripts/python tools/derive_leveling_builds.py <class ...>
    .venv/Scripts/python tools/derive_opponent_kits.py
    (every class report, then wowforever dashboard)

A slot whose guide passes the guard again takes it over the talentsforever.com build. wow-forever.gg's pick rates
(#450) become worth comparing once its window starts after the 3 Nov hotfixes.

## 3. Post-launch logs (#376, #308, #424)
- With the owner's go-ahead: `wowforever foreverlogs-refresh --week <n>`, with weeks counted from 2024-01-01. Fetch
  post-launch weeks only.
- Then `wowforever validate-logs --stats stats-w<n>`. Compare each spec's model/logs ratio with the pre-launch run
  and post the table on #376.
- **#308:** one boss-only request to confirm that `/statistics?bossId=` takes `bosses.json`'s `boss_id`. Then fill
  `config/single_target_bosses.toml`, run `foreverlogs-refresh --variant stats-per-boss` and
  `validate-logs --single-target`.
- **#424:** if Arms (and Fury) still sit under the logs, the Rage formula is the open question: Classic's
  7.5 × damage / c, or TBC's weapon-speed factor.

## 4. In-game checks (#438)
Each guess has a toggle or value in `config/`. Replace it with a dated, patch-tagged result (`tested = "..."` in
`config/assumptions.toml`), then rerun the reports.

| Check | Where | How |
|---|---|---|
| Swiftmend consumes the HoT (now assumed, from the 70707+ tooltip) | `assumptions.toml` `swiftmend_consumes_hot` | Rejuvenation, then Swiftmend: is Rejuvenation still on the target? If it's gone, Bloom shouldn't heal for it either. |
| Leader of the Pack and Moonkin Aura: all crit, whole party, one at a time | `group_buffs.toml` | Druid in cat or moonkin form: does a caster's spell crit rise? Two druids: does it add up? |
| Poised works only out of combat | `classes/rogue.py` UNMODELED | Does Poised trigger in a fight at full Energy? |
| Improved Whirlwind's bonus hits only the closest enemy | `classes/warrior.py` | Whirlwind on 2 mobs: compare the two hits |
| Maelstrom Weapon: 10 procs a minute | `shaman.toml` `maelstrom_weapon.ppm` | Count procs over a few minutes of melee |
| Poison chances: Instant 20%, Deadly 30%, 5 stacks | `rogue.toml` `poisons` | Count applications over 100 hits |
| Mana regen while casting for hunters, paladins and Enhancement | `melee.toml` | Mana over 30 s of casting |
| Level-based spell resistance | `assumptions.toml` `level_resistance` | Partial resists against a +3 target |
| Frostfire Bolt: periodic crits, Impact from ticks, Burning Soul, interrupt lockout, Fingers of Frost | `assumptions.toml` `frostfire_*` | Combat log while casting at a target dummy |
| Mage AoE target cap | `assumptions.toml` `aoe_target_cap` | Blizzard on 6+ mobs: does each mob's damage drop? |
| Thorns spell power coefficient | `assumptions.toml` `thorns_spell_power_coefficient` | Thorns damage with and without spell power gear |

The Berserk cooldown check is gone: Berserk was removed in 70707.
