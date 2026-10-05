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


@dataclass(frozen=True)
class Rotation:
    """Sustained single-target output: filler plus weaves, mana included."""

    dps: float
    mana_per_second: float
    weaves: dict[str, float]            # weave spell name -> casts per minute
    weave_cast_times: dict[str, float]  # weave spell name -> filler time per weave cast


def rotation(char: Character, filler: SpellRank, *, target_level: int,
             assumptions: Assumptions, sustained: bool) -> Rotation:
    """DPS and mana drain of `filler` with the mage's proc/stack weaves."""
    stats = char.stats
    conditions = frozenset({"sustained"}) if sustained else frozenset()
    ranks = {t.name: char.ranks.get(t.talent_id, 0) for t in char.cls.talents}

    def taken(name: str) -> int:
        return ranks.get(name, 0)

    def value(name: str, kind: str) -> float:
        """Per-rank value of a taken talent's `kind` effect; 0 when untaken."""
        talent = next((t for t in char.cls.talents if t.name == name), None)
        rank = taken(name)
        if talent is None or rank <= 0:
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
        )

    filler_mods = mods_for(filler)
    hit = 1.0 - miss_chance(char.level, target_level, stats.hit_pct + filler_mods.hit_bonus) / 100.0
    crit = (stats.crit_pct + filler_mods.crit_chance_bonus) / 100.0
    cast = effective_cast_time(filler, filler_mods)
    if filler.channeled:
        cast = max(cast, filler.duration)
    filler_dps = ev_of(filler, filler_mods) / cast

    weaves: list[tuple[SpellRank, float, float, Modifiers]] = []

    def add(spell: SpellRank, n: float, cast_w: float, mods: Modifiers) -> None:
        weaves.append((spell, n, cast_w, mods))

    if "fire" in filler.schools:
        blast = best_rank(char.spells, "Fire Blast", char.level)
        if blast is not None:
            cooldown = blast.cooldown + value("Wake of Fire", "cooldown")  # Wake of Fire is negative
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
    if fof_rank > 0 and taken("Ice Lance") > 0 and filler.slow_pct > 0:
        lance = best_rank(char.spells, "Ice Lance", char.level)
        if lance is not None:
            # +300% damage vs a frozen target
            frozen = replace(lance, min_damage=lance.min_damage * 4.0,
                             max_damage=lance.max_damage * 4.0,
                             coefficient=lance.coefficient * 4.0)
            chance = value("Fingers of Frost", "proc_chance")
            add(frozen, (60.0 / cast) * chance / 100.0 * fof_rank, GCD_SECONDS,
                mods_for(lance, frozenset({"frozen"})))

    busy = sum(n * cast_w for _, n, cast_w, _ in weaves)
    if busy > 60.0:
        weaves = [(s, n * 60.0 / busy, cast_w, mods) for s, n, cast_w, mods in weaves]
        busy = 60.0

    def cost(spell: SpellRank, mods: Modifiers) -> float:
        cost = spell.mana_cost * (1.0 + mods.mana_cost_pct / 100.0)
        if "fire" in spell.schools or "frost" in spell.schools:
            cost -= spell.mana_cost * moe / 100.0 * hit * crit
        return cost

    dps = filler_dps
    mana_per_second = cost(filler, filler_mods) / cast * (1.0 - busy / 60.0)
    for spell, n, cast_w, mods in weaves:
        gain = ev_of(spell, mods) - filler_dps * cast_w
        dps += n * gain / 60.0
        mana_per_second += n * cost(spell, mods) / 60.0

    return Rotation(
        dps=dps,
        mana_per_second=mana_per_second,
        weaves={s.name: n for s, n, _, _ in weaves},
        weave_cast_times={s.name: cast_w for s, _, cast_w, _ in weaves},
    )
