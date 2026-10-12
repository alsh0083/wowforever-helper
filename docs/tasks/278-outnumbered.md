# Task #278: outnumbered (2v1) world-PvP score

Make `tests/test_outnumbered.py` pass without breaking the rest of the suite. Do not edit the tests. Edit only `config/duel.toml`, `src/wowforever/schema.py`, `src/wowforever/classes/druid.py`, `src/wowforever/pvp/duel.py` and `src/wowforever/pvp/class_pvp.py`. The test docstring has the hand-worked numbers.

## Why
The duel model is 1v1, so Overgrowth (Entangling Roots holds 2 more targets) scores nothing. The owner decided that 2v1 fights get a separate "outnumbered" score next to the PvP score. The defender kills two opponents one at a time. While both are alive, their controls add up and the defender's control is shared between them.

## Change
1. **`config/duel.toml`:** append
   ```toml

   # Outnumbered (2v1, #278): share of the defender's single-target stuns, slows and interrupts each of
   # the two opponents gets while both are alive (estimate: split evenly).
   outnumbered_control_split = 0.5
   ```
2. **`src/wowforever/schema.py`, `EFFECT_KINDS`:** after the `"duration",` line add
   ```python
       "targets",          # more targets a spell can affect at once (count)
   ```
3. **`src/wowforever/classes/druid.py`:**
   - After the `"Improved Regrowth"` entry in `TALENT_EFFECTS`, add
     ```python
         "Overgrowth": (
             EffectRule("targets", r"affected by Entangling Roots by (\d+)", ("Entangling Roots",)),
         ),
     ```
   - In `UNMODELED`, delete the `"Overgrowth": ...` line.
4. **`src/wowforever/pvp/duel.py`:**
   - In `MageSide`, after the `heal_budget` field add
     ```python
         root_targets: int = 1  # opponents its roots hold at once (Overgrowth, #278)
     ```
   - Between `scenario_scores` and `best_scenario_scores`, add
     ```python
     def combined_lockout(kits: Sequence[Kit]) -> float:
         """Seconds per minute several kits together keep the defender cast-locked (#278): each kind adds up
         across kits, and each DR kind is capped for the longest control of that kind in any of them."""
         c = _config()
         out: dict[str, float] = {}
         for kit in kits:
             for kind, seconds in lockout_seconds(kit.controls, kit.energy_per_minute).items():
                 out[kind] = out.get(kind, 0.0) + seconds
         for kind in DR_KINDS & set(out):
             longest = max(ctrl.duration for kit in kits for ctrl in kit.controls if ctrl.kind == kind)
             out[kind] = min(out[kind], 60 * c["dr_chain"] * longest / (c["dr_chain"] * longest + c["dr_immune_seconds"]))
         return sum(out.values())


     def outnumbered(side: MageSide, first: Kit, second: Kit) -> DuelResult:
         """The defender against two opponents at once, killing `first` then `second` (#278).

         Phase 1 (both alive): both kits' lockouts add up; the defender's stuns, slows and interrupts are
         split between them by outnumbered_control_split; roots hold the opponent not being attacked, and
         the attacked one too with root_targets >= 2. Phase 2: `second` alone, as in a duel. Healing happens
         in phase 1 and counts only if the score rises. mage_uptime and opponent_uptime are phase 1's,
         the latter for `first`."""
         c = _config()
         max_fight = c["max_fight"]

         def kill_time(kit: Kit, uptime: float) -> float:
             dps = side.dps + (side.nova_dps if kit.role == "melee" else 0.0)
             immune = kit.immunity[0] / kit.immunity[1] if kit.immunity else 0.0
             return kit.health / (dps * uptime * (1 - immune))

         def incoming(kit: Kit, control: MageSide) -> tuple[float, float]:
             uptime = max(c["min_uptime"], 1 - _kiting_seconds(control, kit, c) / 60)
             physical = side.physical_taken if kit.role in ("melee", "ranged") else 1.0
             return kit.dps * physical * uptime * (1 - side.immunity_share), uptime

         def barrier(kits: Sequence[Kit]) -> float:
             b = side.barrier_per_min / 60
             return b * c["dispel_barrier_factor"] if any(k.dispels_buffs for k in kits) else b

         u1 = max(c["min_uptime"], 1 - combined_lockout([first, second]) / 60)
         u2 = max(c["min_uptime"], 1 - combined_lockout([second]) / 60)
         t1, t2 = kill_time(first, u1), kill_time(second, u2)

         split = c["outnumbered_control_split"]
         shared = dataclasses.replace(side, stun=side.stun * split, slow=side.slow * split,
                                      interrupt=side.interrupt * split)
         focus = dataclasses.replace(shared, root=side.root if side.root_targets >= 2 else 0.0)
         d_first, first_uptime = incoming(first, focus)
         net1 = d_first + incoming(second, shared)[0] - barrier([first, second])
         net2 = incoming(second, side)[0] - barrier([second])

         def time_to_die(health: float, phase1: float) -> float:
             if net1 > 0 and net1 * phase1 >= health:
                 return health / net1
             left = health - max(net1, 0.0) * phase1
             return phase1 + left / net2 if net2 > 0 else max_fight

         t_side = min(t1 + t2, max_fight)
         t_die = min(time_to_die(side.health, t1), max_fight)
         score = t_die / (t_side + t_die)
         if side.heal_budget > 0 and side.heal_hps > 0:
             heal_time = side.heal_budget / side.heal_hps
             h_side = min(t1 + heal_time + t2, max_fight)
             h_die = min(time_to_die(side.health + side.heal_budget, t1 + heal_time), max_fight)
             if h_die / (h_side + h_die) > score:
                 t_side, t_die, score = h_side, h_die, h_die / (h_side + h_die)
         return DuelResult(score=score, t_mage=t_side, t_opponent=t_die, mage_uptime=u1, opponent_uptime=first_uptime)


     def outnumbered_scores(side: MageSide, kits: Sequence[Kit]) -> dict[str, Any]:
         """Mean outnumbered score over every pair of different kits with at least one melee kit (#278),
         each pair in its better kill order; matchups are keyed "id+id" by sorted id."""
         matchups: dict[str, float] = {}
         for i, a in enumerate(kits):
             for b in kits[i + 1:]:
                 if a.id == b.id or "melee" not in (a.role, b.role):
                     continue
                 key = "+".join(sorted((a.id, b.id)))
                 matchups[key] = max(outnumbered(side, a, b).score, outnumbered(side, b, a).score)
         return {"score": sum(matchups.values()) / len(matchups) if matchups else 0.5, "matchups": matchups}
     ```
5. **`src/wowforever/pvp/class_pvp.py`:**
   - Change the import `from wowforever.pvp.duel import Control, Kit, MageSide, lockout_seconds, scenario_scores` to `from wowforever.pvp.duel import Control, Kit, MageSide, lockout_seconds, outnumbered_scores, scenario_scores`.
   - In `class_side`, after the `heal_hps, heal_budget = heal_capacity(...)` line add
     ```python
         # more targets for a root control from taken talents (Overgrowth, #278)
         roots = {c["name"] for c in cfg["controls"] if c["kind"] == "root"}
         extra = sum(e.values[ranks[t.talent_id] - 1] for t in cls.talents if ranks.get(t.talent_id, 0) > 0
                     for e in t.effects if e.kind == "targets" and roots & set(e.applies_to))
     ```
     and in the `MageSide(...)` call after `heal_budget=heal_budget,` add `root_targets=1 + int(extra),`.
   - At the end of the file add
     ```python


     def outnumbered_score(class_name: str, stats: MeleeStats, spells: Sequence[SpellRank], cls: ClassData,
                           ranks: Mapping[int, int], kits: Sequence[Kit]) -> float:
         """Mean 2v1 score over pairs of kits (#278), a separate score next to pvp_score."""
         return outnumbered_scores(class_side(class_name, stats, spells, cls, ranks), kits)["score"]
     ```

Change nothing else.

## Environment note
The package is already installed in `.venv`. Before you start, `tests/test_outnumbered.py` fails at collection with `ImportError` (`outnumbered_score`). That's expected. Install nothing and ask for no elevation. Write the edits with `tools/apply_patch.py` (see AGENTS.md), in the order above, with each file's hunks in file order.

## Done when
`.venv/Scripts/python -m pytest tests/test_outnumbered.py tests/test_duel.py tests/test_class_pvp.py tests/test_hot_heals.py` passes, and so does `.venv/Scripts/python -m pytest -m "not slow"`.
