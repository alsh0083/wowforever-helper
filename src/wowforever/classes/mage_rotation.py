"""Mage single-target rotation: one filler plus its proc/stack weaves (#57).

The model is fixed by docs/tasks/57-rotations.md and pinned by tests/test_rotation.py:
the filler runs between weaves - Fire Blast on its cooldown, Scorch upkeep while
sustained, Pyroblast off Heating Up, and frozen Ice Lance off Fingers of Frost.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from wowforever.assumptions import Assumptions, periodic_can_crit, sub20_penalized
from wowforever.calc.ev import (
    GCD_SECONDS, Modifiers, effective_cast_time, expected_damage, miss_chance,
)
from wowforever.calc.talents import modifiers_for
from wowforever.schema import SpellRank
from wowforever.scenarios import Character, best_rank, scaled

ARCANE_POWER_COOLDOWN = 180.0  # seconds; Arcane Power's 15 s buff is averaged over it
FREEZE_SECONDS = 5.0           # Frostbite: "Freeze the target for 5 sec."


@dataclass(frozen=True)
class Rotation:
    """Sustained single-target output: filler plus weaves, mana included."""

    dps: float
    mana_per_second: float
    weaves: dict[str, float]            # weave spell name -> casts per minute
    weave_cast_times: dict[str, float]  # weave spell name -> filler time per weave cast


def frozen_lance_multiplier(cls) -> float:
    """Ice Lance's damage multiplier on a frozen target, from its talent's rank text ("Deals N% increased damage
    to Frozen targets": 1 + N/100; 200% on 1.60.1.70425, #354)."""
    import re

    text = cls.talent_named("Ice Lance").rank_text[-1]
    return 1 + float(re.search(r"Deals (\d+(?:\.\d+)?)% increased damage to Frozen targets", text).group(1)) / 100


def combustion_rule(cls) -> tuple[float, int]:
    """Combustion's (crit % per Fire hit, crits until it ends) from its rank text (#394)."""
    import re

    text = cls.talent_named("Combustion").rank_text[-1]
    step = re.search(r"critical strike chance with Fire damage spells by (\d+(?:\.\d+)?)%", text).group(1)
    limit = re.search(r"until you have caused (\d+) non-periodic critical strikes", text).group(1)
    return float(step), int(limit)


def combustion_extra_crits(p: float, hit: float, step: float, limit: int) -> float:
    """Expected extra crit chance summed over the casts while Combustion lasts (#394). Cast i (from 0) crits with
    min(1, p + step x i) instead of p; a cast crits with `hit` x that chance, and Combustion ends after `limit`
    crits. Exact over the number of crits so far, cut off once it has ended with certainty (or after 200 casts)."""
    active = [1.0] + [0.0] * (limit - 1)    # chance of being on c crits, Combustion still up
    extra, i = 0.0, 0
    while sum(active) > 1e-12 and i < 200:
        chance = min(1.0, p + step * i)
        extra += sum(active) * (chance - p)
        q = hit * chance
        nxt = [0.0] * limit
        for c, pr in enumerate(active):
            nxt[c] += pr * (1 - q)
            if c + 1 < limit:
                nxt[c + 1] += pr * q
        active, i = nxt, i + 1
    return extra


def missile_barrage_rule(cls, rank: int) -> dict[str, float]:
    """Missile Barrage's proc chance (%) at `rank`: per cast of each spell named in the rank text, and per missile
    hit for "Arcane Missiles" when the text has that clause (0 on 70685, where it was dropped, #439)."""
    import re

    text = cls.talent_named("Missile Barrage").rank_text[rank - 1]
    blast = float(re.search(r"Arcane Blast spell a (\d+(?:\.\d+)?)% chance", text).group(1))
    missile = re.search(r"your Arcane Missile hits a (\d+(?:\.\d+)?)% chance", text)
    clause = re.search(r"and your ([A-Z][\w ,]*?) spells a (\d+(?:\.\d+)?)% chance", text)
    rule: dict[str, float] = {"Arcane Blast": blast,
                              "Arcane Missiles": float(missile.group(1)) if missile else 0.0}
    for name in re.split(r", and |, | and ", clause.group(1)):
        rule[name] = float(clause.group(2))
    return rule


def frozen_hit_gain(char: Character, filler: SpellRank, *, target_level: int,
                    assumptions: Assumptions) -> float:
    """Extra damage of one hit on a frozen target (Frost Nova, #97) over spending that time on
    the filler: a 4x Ice Lance with Shatter's crit when Ice Lance is taken, otherwise the filler
    with Shatter's crit (0 without Shatter). One hit per freeze: the first hit breaks the root."""
    ranks = char.ranks

    def ev_of(spell: SpellRank, conditions: frozenset[str]) -> float:
        return expected_damage(
            sub20_penalized(scaled(spell, char.level), assumptions),
            spell_power=char.stats.spell_power, crit_pct=char.stats.crit_pct,
            hit_pct=char.stats.hit_pct, caster_level=char.level, target_level=target_level,
            mods=modifiers_for(spell, char.cls, ranks, conditions),
            periodic_can_crit=periodic_can_crit(spell.name, assumptions),
            level_resistance=bool(assumptions["level_resistance"]),
        )

    lance_taken = any(t.name == "Ice Lance" and ranks.get(t.talent_id, 0) > 0 for t in char.cls.talents)
    lance = best_rank(char.spells, "Ice Lance", char.level) if lance_taken else None
    frozen = frozenset({"frozen"})
    if lance is not None:
        x = frozen_lance_multiplier(char.cls)
        quad = replace(lance, min_damage=lance.min_damage * x, max_damage=lance.max_damage * x,
                       coefficient=lance.coefficient * x)
        mods = modifiers_for(filler, char.cls, ranks, frozenset())
        cast = effective_cast_time(filler, mods)
        if filler.channeled:
            cast = max(cast, filler.duration)
        return ev_of(quad, frozen) - ev_of(filler, frozenset()) / cast * GCD_SECONDS
    return ev_of(filler, frozen) - ev_of(filler, frozenset())


def arcane_blast_stacks(cls) -> tuple[float, float, int, float] | None:
    """Arcane Blast's stacking buff from its talent's rank text (1.60.1.70425, #355): (% of Intellect as spell
    damage per stack, % mana cost increase per stack, max stacks, buff seconds), or None without that text."""
    import re

    try:
        text = cls.talent_named("Arcane Blast").rank_text[-1]
    except KeyError:
        return None
    m = re.search(r"gain (\d+(?:\.\d+)?)% of your Intellect as Spell Damage and the mana cost of Arcane Blast is "
                  r"increased by (\d+(?:\.\d+)?)%\. Effect stacks up to (\d+) times and lasts (\d+(?:\.\d+)?) sec", text)
    if m is None:
        return None
    return float(m.group(1)), float(m.group(2)), int(m.group(3)), float(m.group(4))


def rotation(char: Character, filler: SpellRank, *, target_level: int,
             assumptions: Assumptions, sustained: bool, blast_stacks: int = 0) -> Rotation:
    """DPS and mana drain of `filler` with the mage's proc/stack weaves; with `blast_stacks` n > 0, each Arcane
    Blast buff window opens with n Arcane Blasts and the filler casts the rest of it with n stacks (#355)."""
    stats = char.stats
    conditions = frozenset({"sustained"}) if sustained else frozenset()
    ranks = {t.name: char.ranks.get(t.talent_id, 0) for t in char.cls.talents}

    def taken(name: str) -> int:
        return ranks.get(name, 0)

    def value(name: str, kind: str) -> float:
        """Per-rank value of a taken talent's `kind` effect; 0 when untaken."""
        try:
            talent = char.cls.talent_named(name)      # accepts a patch's renamed talent (config/talent_renames.toml)
        except KeyError:
            return 0.0
        rank = char.ranks.get(talent.talent_id, 0)
        if rank <= 0:
            return 0.0
        for effect in talent.effects:
            if effect.kind == kind:
                return effect.values[rank - 1]
        return 0.0

    scorch_taken = taken("Improved Scorch") > 0
    arcane_power = taken("Arcane Power") > 0
    heating_up = taken("Heating Up") > 0
    moe = value("Master of Elements", "resource")

    def mods_for(spell: SpellRank, extra_conditions: frozenset[str] = frozenset()) -> Modifiers:
        """Talent modifiers, plus the sustained buffs when `sustained`."""
        mods = modifiers_for(spell, char.cls, char.ranks, extra_conditions or conditions)
        if sustained:
            if scorch_taken and "fire" in filler.schools and "fire" in spell.schools:
                mods = replace(mods, damage_pct=mods.damage_pct + 15.0)  # 5 stacks x 3%
            if arcane_power:
                share = 30.0 * 15.0 / ARCANE_POWER_COOLDOWN
                mods = replace(mods, damage_pct=mods.damage_pct + share,
                               mana_cost_pct=mods.mana_cost_pct + share)
        return mods

    def ev_of(spell: SpellRank, mods: Modifiers) -> float:
        return expected_damage(
            sub20_penalized(scaled(spell, char.level), assumptions),
            spell_power=stats.spell_power,
            crit_pct=stats.crit_pct,
            hit_pct=stats.hit_pct,
            caster_level=char.level,
            target_level=target_level,
            mods=mods,
            periodic_can_crit=periodic_can_crit(spell.name, assumptions),
            level_resistance=bool(assumptions["level_resistance"]),
        )

    filler_mods = mods_for(filler)
    hit = 1.0 - miss_chance(char.level, target_level, stats.hit_pct + filler_mods.hit_bonus) / 100.0
    crit = (stats.crit_pct + filler_mods.crit_chance_bonus) / 100.0
    cast = effective_cast_time(filler, filler_mods)
    if filler.channeled:
        cast = max(cast, filler.duration)
    barrage = (missile_barrage_rule(char.cls, taken("Missile Barrage")) if taken("Missile Barrage") > 0
               else {})
    barrage_share = 0.0     # Arcane Missiles filler: the share of its casts that are barrages (#394)
    if filler.name == "Arcane Missiles" and barrage and filler.tick_period > 0:
        missiles = round(filler.duration / filler.tick_period)
        barrage_share = 1 - (1 - hit * barrage["Arcane Missiles"] / 100.0) ** missiles
        cast *= 1 - barrage_share / 2
    filler_ev = ev_of(filler, filler_mods)

    # Frostbite (#96): on normal mobs a landed Chill can freeze the target for FREEZE_SECONDS, and
    # the filler casts that land inside the freeze get Shatter's crit. Bosses (sustained) can't be
    # frozen. A cast lands frozen when any of the previous floor(freeze / cast) casts procced.
    freeze_procs = 0.0  # Frostbite freezes per filler cast
    if not sustained and filler.slow_pct > 0:
        freeze_procs = value("Frostbite", "proc_chance") / 100.0 * hit
        if freeze_procs > 0:
            inside = int(FREEZE_SECONDS // cast)
            frozen_share = 1.0 - (1.0 - freeze_procs) ** inside
            frozen_mods = mods_for(filler, conditions | {"frozen"})
            filler_ev = (1.0 - frozen_share) * filler_ev + frozen_share * ev_of(filler, frozen_mods)
    filler_dps = filler_ev / cast

    weaves: list[tuple[SpellRank, float, float, Modifiers]] = []

    def add(spell: SpellRank, n: float, cast_w: float, mods: Modifiers) -> None:
        weaves.append((spell, n, cast_w, mods))

    if "fire" in filler.schools:
        blast = best_rank(char.spells, "Fire Blast", char.level)
        if blast is not None:
            cooldown = blast.cooldown + value("Improved Fire Blast", "cooldown")  # negative
            if cooldown > 0:
                add(blast, 60.0 / cooldown, GCD_SECONDS, mods_for(blast))
    if sustained and scorch_taken and "fire" in filler.schools:
        scorch = best_rank(char.spells, "Scorch", char.level)
        if scorch is not None:
            chance = value("Improved Scorch", "proc_chance")
            if chance > 0:
                # one landed stack refresh per 30 s
                add(scorch, 2.0 * 100.0 / chance, scorch.cast_time, mods_for(scorch))
    if (sustained and heating_up and taken("Pyroblast") > 0
            and filler.name in ("Fireball", "Frostfire Bolt")):
        pyro = best_rank(char.spells, "Pyroblast", char.level)
        if pyro is not None:
            # one landed filler crit per Heating Up stack, three stacks per Pyroblast
            add(pyro, (60.0 / cast) * hit * crit / 3.0, pyro.cast_time * 0.25, mods_for(pyro))
    fof_rank = taken("Fingers of Frost")
    if (fof_rank > 0 or freeze_procs > 0) and taken("Ice Lance") > 0 and filler.slow_pct > 0:
        lance = best_rank(char.spells, "Ice Lance", char.level)
        if lance is not None:
            # Ice Lance's frozen bonus: each Fingers of Frost charge, and one per freeze
            x = frozen_lance_multiplier(char.cls)
            frozen = replace(lance, min_damage=lance.min_damage * x,
                             max_damage=lance.max_damage * x,
                             coefficient=lance.coefficient * x)
            chance = value("Fingers of Frost", "proc_chance") / 100.0 * fof_rank
            add(frozen, (60.0 / cast) * (chance + freeze_procs), GCD_SECONDS,
                mods_for(lance, conditions | {"frozen"}))

    if filler.name != "Arcane Missiles" and barrage.get(filler.name, 0.0) > 0:
        # a landed filler cast can proc a free, half-length Arcane Missiles: woven in when it gains (#394)
        missiles = best_rank(char.spells, "Arcane Missiles", char.level)
        if missiles is not None:
            free, missile_mods = replace(missiles, mana_cost=0), mods_for(missiles)
            if ev_of(free, missile_mods) > filler_dps * missiles.duration / 2:
                add(free, (60.0 / cast) * hit * barrage[filler.name] / 100.0, missiles.duration / 2, missile_mods)

    blast = best_rank(char.spells, "Arcane Blast", char.level) if blast_stacks > 0 else None
    stacks = arcane_blast_stacks(char.cls) if blast is not None else None
    window_bonus = 0.0     # filler DPS gained inside the buff windows, per second of the minute
    if stacks is not None:
        sp_pct, cost_pct, max_stacks, seconds = stacks
        n = min(blast_stacks, max_stacks)
        windows = 60.0 / seconds
        per_stack = sp_pct / 100.0 * stats.intellect             # spell damage per stack
        blast_mods = mods_for(blast)
        for k in range(n):                                       # the k-th Arcane Blast casts with k stacks
            extra = blast.coefficient * per_stack * k
            add(replace(blast, min_damage=blast.min_damage + extra, max_damage=blast.max_damage + extra,
                        mana_cost=blast.mana_cost * (1 + cost_pct / 100.0 * k)),
                windows, effective_cast_time(blast, blast_mods), blast_mods)
        rest = max(0.0, seconds - n * effective_cast_time(blast, blast_mods)) / seconds
        lift = filler.coefficient * per_stack * n
        boosted = replace(filler, min_damage=filler.min_damage + lift, max_damage=filler.max_damage + lift)
        window_bonus = (ev_of(boosted, filler_mods) - ev_of(filler, filler_mods)) / cast * rest
    busy = sum(n * cast_w for _, n, cast_w, _ in weaves)
    if busy > 60.0:
        weaves = [(s, n * 60.0 / busy, cast_w, mods) for s, n, cast_w, mods in weaves]
        busy = 60.0

    def cost(spell: SpellRank, mods: Modifiers) -> float:
        cost = spell.mana_cost * (1.0 + mods.mana_cost_pct / 100.0)
        if "fire" in spell.schools or "frost" in spell.schools:
            cost -= spell.mana_cost * moe / 100.0 * hit * crit
        return cost

    dps = filler_dps + window_bonus * (1.0 - busy / 60.0)
    mana_per_second = cost(filler, filler_mods) * (1 - barrage_share) / cast * (1.0 - busy / 60.0)
    for spell, n, cast_w, mods in weaves:
        gain = ev_of(spell, mods) - filler_dps * cast_w
        dps += n * gain / 60.0
        mana_per_second += n * cost(spell, mods) / 60.0

    if sustained and taken("Presence of Mind") > 0:
        # one instant cast per cooldown: a GCD of filler time for the filler or Pyroblast, whichever gains more (#394)
        pom = best_rank(char.spells, "Presence of Mind", char.level)
        options = [] if filler.channeled else [(filler, filler_mods)]   # a channel can't be made instant
        pyro = best_rank(char.spells, "Pyroblast", char.level) if taken("Pyroblast") > 0 else None
        if pyro is not None:
            options.append((pyro, mods_for(pyro)))
        if pom is not None and pom.cooldown > 0 and options:
            spell, mods = max(options, key=lambda o: ev_of(*o))
            dps += (ev_of(spell, mods) - filler_dps * GCD_SECONDS) / pom.cooldown
            # its mana, less the filler's for the GCD it takes
            mana_per_second += ((cost(spell, mods) - cost(filler, filler_mods) * GCD_SECONDS / cast)
                                / pom.cooldown)
    if sustained and taken("Combustion") > 0 and "fire" in filler.schools:
        # Fire crit rising per cast until a few crits, once per cooldown (#394)
        combustion = best_rank(char.spells, "Combustion", char.level)
        if combustion is not None and combustion.cooldown > 0:
            step, limit = combustion_rule(char.cls)
            plus = replace(filler_mods, crit_chance_bonus=filler_mods.crit_chance_bonus + 1.0)
            per_crit = (ev_of(filler, plus) - ev_of(filler, filler_mods)) / 0.01
            extra = combustion_extra_crits(min(1.0, crit), hit, step / 100.0, limit)
            dps += extra * per_crit / combustion.cooldown

    return Rotation(
        dps=dps,
        mana_per_second=mana_per_second,
        weaves={s.name: n for s, n, _, _ in weaves},
        weave_cast_times={s.name: cast_w for s, _, cast_w, _ in weaves},
    )
