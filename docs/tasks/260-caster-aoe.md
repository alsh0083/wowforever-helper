# Task #260: AoE pulls for casters

Make `tests/test_caster_aoe.py` pass without breaking the rest of the suite. Do not edit the tests. Edit only `config/casters.toml`, `config/assumptions.toml` and `src/wowforever/caster.py`. The test docstring has the hand-worked numbers.

## Why
The owner chose option 3 of #248: every class gets a separate "AoE pulls" score, like the mage's, and the dungeon score stays single-target. This task adds the caster engine's part: seconds to clear a pack with the best AoE spell mixed into the rotation, or with the rotation alone. Showing it in the report is #263.

## Change
1. **`config/casters.toml`:**
   - In `[priest]`, after `regen_spirit_div = 4` (the line just before `[priest.weights]`), add
     ```toml
     # AoE pulls (#260): spells tried against a pack, besides the single-target rotation
     aoe_spells = ["Holy Nova"]
     ```
   - In `[warlock]`, after `extra_regen_per_second = 15.0`, add `aoe_spells = ["Rain of Fire", "Hellfire"]`.
   - In `[druid]`, after its `regen_spirit_div = 5` line (just before `[druid.weights]`), add `aoe_spells = ["Hurricane"]`.
   - In `[shaman]`, after its `regen_spirit_div = 5` line (just before `[shaman.weights]`), add
     ```toml
     # Magma Totem's damage sits in a triggered spell the normalizer doesn't read yet
     aoe_spells = ["Chain Lightning", "Fire Nova"]
     # targets a jumping spell hits at most (Classic: Chain Lightning 3; Forever's data has no count); 0 = every mob
     aoe_max_targets = { "Chain Lightning" = 3 }
     ```
2. **`config/assumptions.toml`:** append
   ```toml

   [chain_jump_falloff_pct]
   value = 30
   options = [30, 0]
   why = "Chain Lightning loses damage on each jump in Classic (30%); Forever's client data has neither the falloff nor the target count (#260)."
   source = "Classic Chain Lightning text; dataset 1.60.1.70291 (MaxTargets 0, no falloff field)"
   tested = ""
   talents = ["Chain Lightning"]
   ```
3. **`src/wowforever/caster.py`:**
   - In the module docstring, replace the line `Not modeled here: procs, cleave or AoE, pets (warlock, #165) and Life Tap; classes add those.` with
     ```
     AoE pulls (#260): seconds to clear a pack with the best of the class's `aoe_spells` mixed into the
     rotation, or the rotation alone.

     Not modeled here: procs, cleave, pets (warlock, #165) and Life Tap; classes add those.
     ```
   - Just before `def spirit_regen(`, add
     ```python
     @dataclass(frozen=True)
     class AoePull:
         seconds: float   # to clear the pack
         spell: str       # the AoE spell used, or "single target"


     ```
   - At the end of the file, add
     ```python


     def chain_hits(pack: int, max_targets: int, falloff_pct: float) -> float:
         """Targets' worth of damage one cast deals to a pack (#260): every mob when max_targets is 0, else
         min(pack, max_targets) hits, each jump dealing falloff_pct% less than the one before."""
         if max_targets <= 0:
             return float(pack)
         return sum((1 - falloff_pct / 100) ** k for k in range(min(pack, max_targets)))


     def pull_seconds(pack: int, mob_hp: float, single_dps: float, ev: float, seconds: float, period: float,
                      hits: float) -> float:
         """Seconds to clear `pack` mobs of `mob_hp` casting an AoE spell once per `period` (its cast time or
         cooldown, whichever is longer) and the single-target rotation in between (#260). Damage counts against
         the pack's total health; overkill and mobs dying early aren't modeled."""
         rate = ev * hits / period + (1 - seconds / period) * single_dps
         return pack * mob_hp / rate


     def aoe_pull(class_name: str, stats: Stats, spells: Sequence[SpellRank], cls: ClassData,
                  ranks: Mapping[int, int], pack: int, mob_hp: float, *,
                  assumptions: Assumptions | None = None) -> AoePull:
         """The fastest way to clear `pack` same-level mobs of `mob_hp` (#260): each of the class's
         `aoe_spells` (config/casters.toml) mixed into the rotation, or the rotation alone. A spell taught by
         a talent needs that talent; Hellfire's damage to the caster isn't modeled."""
         if assumptions is None:
             assumptions = Assumptions.load()
         cfg = caster_config(class_name)
         single_dps = caster_rotation(class_name, stats, spells, cls, ranks, Target(0, 0)).dps
         best = AoePull(pack * mob_hp / single_dps, "single target")
         talent_ids = {t.name: t.talent_id for t in cls.talents}
         for name in cfg.get("aoe_spells", ()):
             if name in talent_ids and ranks.get(talent_ids[name], 0) <= 0:
                 continue
             spell = best_rank(spells, name, stats.level)
             if spell is None:
                 continue
             ev, seconds, _ = cast(spell, stats, cls, ranks, stats.level, assumptions)
             if ev <= 0:
                 continue
             cooldown = spell.cooldown + sum(
                 e.values[ranks[t.talent_id] - 1] for t in cls.talents if ranks.get(t.talent_id, 0) > 0
                 for e in t.effects if e.kind == "cooldown" and name in e.applies_to)
             hits = chain_hits(pack, cfg.get("aoe_max_targets", {}).get(name, 0), assumptions["chain_jump_falloff_pct"])
             t = pull_seconds(pack, mob_hp, single_dps, ev, seconds, max(seconds, cooldown), hits)
             if t < best.seconds:
                 best = AoePull(t, name)
         return best
     ```

Change nothing else.

## Environment note
The package is already installed in `.venv`. Before you start, `tests/test_caster_aoe.py` fails at collection with `ImportError` (`aoe_pull`). That's expected. Install nothing and ask for no elevation. Write the edits with `tools/apply_patch.py` (see AGENTS.md), in the order above, with each file's hunks in file order. `config/casters.toml` has two `regen_spirit_div = 5` lines (druid and shaman): include the following `[druid.weights]` or `[shaman.weights]` line in each hunk's context so it matches once.

## Done when
`.venv/Scripts/python -m pytest tests/test_caster_aoe.py tests/test_caster_engine.py tests/test_caster_classes.py` passes, and so does `.venv/Scripts/python -m pytest -m "not slow"`.
