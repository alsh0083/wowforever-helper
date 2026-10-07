# Party buffs in the dungeon score (planning, 2026-10-07)

Owner request: model group buffs for a normal 5-player dungeon group (one tank, one healer, three DPS) across
every composition, with stacking handled properly. Follows #172: melee is 0.6-0.8 of the strong boss parses,
and the saved reports show party help (totems, Windfury, attack-power buffs) in melee damage.

## Scope

- **In:** the dungeon scenario. Its score at every checkpoint, the PvE score's dungeon part (so model picks,
  matrix percentages and stat weights see it), and `validate-logs`.
- **Out, for now:**
  - Questing, which is solo; self-buffs stay as they are.
  - PvP duels.
  - Raids, which are 40-player groups. The same catalog can serve them later with a raid composition model.

## The group

- **Shape:** you plus a tank, a healer and two other DPS, all at your level.
- **Tank:** Protection warrior, Protection paladin or Bear druid.
- **Healer:** Holy or Discipline priest, Holy paladin, Restoration druid or Restoration shaman.
- **DPS:** any class's DPS trees (about 19 specs).
- **Raw count:** about 3 × 4 × 190 two-DPS pairs ≈ 2,300 groups per scored build.

## Buff catalog (`config/group_buffs.toml`)

- **What it holds:** one entry per group buff or target debuff that changes damage, about 35 in all. Each has:
  - its provider (class, and spec or talent where needed: Trueshot Aura needs Marksmanship, Leader of the
    Pack needs Feral, Windfury Totem needs Enhancement or the right level);
  - its stacking group;
  - its effect kind (stat, attack power, spell power, crit, hit, haste, damage %, armor reduction, school
    damage taken);
  - who it reaches (party, melee, casters, the target).
- **Values come from the game client's own spell tables** (SpellName / SpellLevels / SpellEffect, already cached
  for each build): the best rank learned at the group's level.
  - Forever changed several (Battle Shout 139 attack power at 60; Trueshot Aura has Forever-only ranks).
  - A patch updates them with the next `update`, no hand-edits.
  - Talents that improve a buff (Improved Battle Shout, Improved Blessings) are read from the provider spec's
    usual talents and marked as such.
- **Unknown values** are marked low confidence and listed on the page. Examples: Forever removed totem
  twisting, and the Legacy perk Permanence extends buff durations.

## Stacking

Stacking is what collapses the group space:
- **Same buff from two players counts once** (two Battle Shouts, two Fortitudes).
- **Buffs in one group take the strongest:**
  - attack-power shouts and blessings stack with each other but not with themselves;
  - Strength of Earth vs Mark of the Wild's strength: different groups, both count;
  - Sunder Armor vs Expose Armor: the stronger wins;
  - Curse of Recklessness vs Curse of the Elements: one curse per warlock.
- **One per provider:**
  - one totem per element per shaman;
  - one blessing per paladin on you;
  - one curse per warlock.
- **The provider picks the option that helps you most:** the best totem per element, the best blessing, the
  best curse. That's an upper bound per composition, written down as an assumption.

Each composition reduces to its *effective buff set*. Many compositions share one (a party with two
warriors is the same as one), so the engine runs once per distinct set, a few hundred per build and level.

## Composition weights

How likely each group is:
- **Classes:** from Forever Logs, how often each class appears in the tank, healer and DPS roles. The public
  statistics API takes `role=tank|support|dps`, about 40 requests per role, on demand, with the owner's key.
- **Specs within a class:** spread by the same API's spec counts.
- **No data:** uniform, flagged.

## Outputs

- **Dungeon score per build and checkpoint:** the expected value over weighted compositions, plus a typical
  range (10th to 90th percentile group), plus the solo value for comparison.
- **The PvE score uses the expected value.** Matrix percentages, model picks and stat weights follow.
- **Page:** the score tables show "with a typical group" and the range on hover; build descriptions mention
  which buffs matter most to the build ("gains most from Windfury Totem and Battle Shout").
- **`validate-logs`** compares grouped dungeon DPS with the boss-only parses again (the #172 check).

## Engine plumbing

- **A `GroupEffects` value (in `src/wowforever/group.py`)** carries:
  - stat adds (strength, agility, stamina, intellect, spirit);
  - attack power and ranged attack power;
  - spell power;
  - crit, spell crit and hit;
  - melee and spell haste;
  - physical and per-school damage multipliers;
  - target armor reduction;
  - per-school damage taken.
- **Stats-level effects are applied once** to the stats object before the engine runs. That works for every
  engine.
- **Damage multipliers, haste and target debuffs need a hook in each of the nine class rotations** (mage,
  caster engine, rogue, hunter, warrior, paladin, cat druid, Enhancement shaman). This is the bulk of the
  engine work. Each gets a test that a buff changes damage by the expected amount.

## Phases (one PR each)

1. **Catalog.** `group_buffs.toml`, a reader that resolves ranks and values from the client tables by level,
   stacking groups, and the effective-set reduction. Tests: rank-by-level values, stacking cases, set dedupe.
2. **Engines.** `GroupEffects` and the hooks in all nine rotations; tests per engine.
3. **Groups.** Composition enumeration, Forever Logs role weights (fetch on demand), expected value and
   range per build and checkpoint. Wired into the dungeon score and the PvE score; all reports regenerated.
4. **Check and show.**
   - `validate-logs` against boss-only parses; findings in `docs/research/log-calibration.md`, closing or
     updating #172.
   - Page: grouped dungeon score with range, the buffs that matter in "About this build", the assumptions
     list.
   - README.

## Decisions taken (defaults; change any)

- **D1 Provider choice:** each provider uses the option best for you (best totem, blessing, curse). It's an
  upper bound, and simple to state.
- **D2 Armor debuffs on bosses:** a warrior tank keeps 5 Sunders up; a paladin or druid tank applies none
  (Faerie Fire comes from any druid).
- **D3 Weights:** Forever Logs role and class shares, uniform where there's no data.
- **D4 Levels:** everyone in the group is your level.
- **D5 Raids:** out of scope until a raid composition model exists.

## Cost

- **Compute:** about 75 builds × 5 checkpoints × a few hundred buff sets is about 150,000 dungeon evaluations
  per full regeneration, minutes in all. The talent-path optimizer stays solo, so leveling orders don't
  slow down.
- **Network:** the role weights add about 80 Forever Logs requests, run on demand only.
