# PvP duel model (#26)

How the world-PvP scenarios turn a mage build and an opposing class into a score. Owner decisions (2026-10-05): model real classes, one typical PvP spec each (a second where consensus says it's common); same level and equivalent gear; in the open world the mage sees the opponent at 30 yards, in an ambush the opponent opens; plus a "melee opens" variant. Battlegrounds stay group fights (#27).

## Shape: a time-to-kill race with control and defenses

A duel is scored as two expected times:

- **T_mage** = opponent health / the mage's *effective* DPS on them
- **T_opp** = mage effective health / the opponent's *effective* DPS on the mage

Score = T_opp / (T_opp + T_mage), from 0 (mage always loses) to 1 (always wins), 0.5 = even. It's a ratio of expectations, not a probability, and it's labelled that way.

## Mage side

- **Damage:** the rotation DPS (#57) against a same-level target, times **casting uptime**: the share of the fight the mage can cast. Uptime drops for time spent stunned, silenced or locked out by the opponent, and time spent moving to kite. Kiting time is offset by instants (Fire Blast, Ice Lance, Frost Nova).
- **Effective health:** health + Ice Barrier absorbs over T_opp + Mana Shield (if the build uses it) + **immunity seconds**. Ice Block (+ Cold Snap) removes that many seconds of the opponent's damage.

## Opponent side (per class/spec)

An **opponent kit** in `config/opponents/<class>-<spec>.toml`, with each number traced to the class's spell data where the data has it:

- health and sustained DPS at the level (gear-equivalent; low confidence until #68 or real data)
- **burst opener**: damage in the first seconds when they open (rogue Ambush/Cheap Shot, warrior Charge, hunter Aimed Shot)
- **controls on the mage**: stuns, silences, interrupts (lockout seconds), with cooldowns
- **gap closers and speed**: Charge/Intercept, Sprint, Feral Charge, Blink-like effects
- **removal of mage control**: trinket-like escapes, Freedom/Escape Artist style breaks, dispels (Priest/Paladin dispel slows and roots)
- **range**: melee or ranged

## Where control and range matter

The opponent's effective DPS on the mage = sustained DPS × their **uptime**: the share of the fight they can hit the mage.

- **Melee vs mage:** uptime falls with the mage's slow, root and stun seconds (the control axis, #25) and rises with the opponent's gap closers and control removal. Kiting only works from range, so the "melee opens" variant starts at uptime 1 for the opener window.
- **Casters vs mage:** uptime falls with the mage's interrupt and silence seconds; slows matter little. Pushback protection (Burning Soul, Ice Barrier) protects the mage's own casting uptime.
- **Stealth openers:** the ambush variant gives the opponent their burst opener and starting stun before the mage acts.

## Matchups and the scenario scores

For each mage build, the duel score against every opponent kit, per variant (mage sees them / they open). The scenario score is the mean over opponents in that scenario: `wpvp_melee` = the melee kits, `wpvp_caster` = caster kits, `stealth_ambush` = stealth openers in the ambush variant. The table of individual matchups goes in the report for the dashboard.

## Confidence

Low. Kits come from spell data and consensus for which spec is typical; health and DPS levels are estimates until gear data (#68) or real parses (#69). The score's main value is **comparing mage builds against the same opponent**, not predicting fights.

## Out of scope for v1

Healing during the fight, resistances and Fire/Frost Ward, diminishing returns on control, trinkets and engineering, line of sight.
