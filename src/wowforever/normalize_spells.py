"""Normalize wago.tools spell tables into trainable SpellRank rows for a class.

`class_spells` keeps the SkillLineAbility rows of the class's skill lines (no Season
of Discovery runes, no level-0 NPC versions) and fills one SpellRank per spell from
the joined spell tables. Area-triggered periodics (Blizzard, Flamestrike) borrow
their tick damage from the matching tick spell, which is itself not trainable.
Channeled periodics with a periodic trigger (Arcane Missiles) borrow their per-tick
damage from the triggered missile spell, which is likewise not trainable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from wowforever.normalize import Tables
from wowforever.schema import SpellRank

SCHOOL_BITS = (
    (1, "physical"), (2, "holy"), (4, "fire"), (8, "nature"),
    (16, "frost"), (32, "shadow"), (64, "arcane"),
)

EFFECT_DAMAGE = 2            # school damage
EFFECT_AURA = 6              # apply aura (DoT, slow, area-periodic marker)
EFFECT_AREA_TRIGGER = 179    # triggers an area effect
EFFECT_COMBO_POINTS = 30     # grant combo points (EffectMiscValue_0 4)
EFFECT_WEAPON_PCT = 31       # percent weapon damage (base points = percent)
EFFECT_TRIGGER_SPELL = 64    # trigger a spell
EFFECT_WEAPON_DAMAGE = 58    # weapon damage
EFFECT_NORMALIZED_WEAPON = 121  # normalized weapon damage (speed set by weapon type)
AURA_DOT = 3                 # periodic damage over time
AURA_PERIODIC_TRIGGER = 23   # periodic trigger: fires EffectTriggerSpell every EffectAuraPeriod
AURA_SLOW = 33               # movement speed mod (negative base points = slow)
AURA_AREA_PERIODIC = 226     # marker for an area-triggered periodic
AURA_CONFUSE = 5             # disorient (Scatter Shot, Blind; Polymorph also has it)
AURA_FEAR = 7                # fear (Fear, Psychic Scream, Intimidating Shout, Death Coil)
AURA_STUN = 12               # stun (Impact's proc; Ice Block also self-stuns, see AURA_IMMUNITY)
AURA_ROOT = 26               # root (Frost Nova, Frostbite's freeze)
AURA_IMMUNITY = 39           # school immunity (Ice Block)
AURA_TRANSFORM = 56          # transform / incapacitate (Polymorph)
AURA_ABSORB = 69             # school damage absorb (Ice Barrier, Fire/Frost Ward)
AURA_MANA_SHIELD = 97        # absorb paid with mana (Mana Shield)
AURA_MELEE_HASTE = 319       # melee haste (Slice and Dice)
EFFECT_INTERRUPT = 68        # interrupt + school lockout (Counterspell)

_ACQUIRE_RUNE = 3            # SkillLineAbility.AcquireMethod: Season of Discovery rune
_ATTR1_CHANNELED = 0x4 | 0x40  # SpellMisc.Attributes_1 channel flags (Arcane Missiles / Blizzard)


def class_spells(tables: Tables, *, skill_lines: Sequence[int]) -> tuple[SpellRank, ...]:
    """Every trainable spell rank of the class, sorted by (name, rank)."""
    lines = {int(line) for line in skill_lines}
    sla_spells = {int(row["Spell"]) for row in tables["SkillLineAbility"]}
    names = {int(row["ID"]): row["Name_lang"] for row in tables["SpellName"]}
    levels = _by_spell(tables["SpellLevels"])

    trainable: list[tuple[str, int, int]] = []
    seen: set[int] = set()
    for row in tables["SkillLineAbility"]:
        if int(row["SkillLine"]) not in lines or int(row["AcquireMethod"]) == _ACQUIRE_RUNE:
            continue
        spell_id = int(row["Spell"])
        if spell_id in seen:
            continue
        seen.add(spell_id)
        level_row = levels.get(spell_id)
        if level_row is None:
            continue
        level = int(_f(level_row["BaseLevel"]))
        if level <= 0:
            continue
        name = names.get(spell_id)
        if name is None:
            raise ValueError(f"skill line {row['SkillLine']}: no SpellName for spell {spell_id}")
        trainable.append((name, level, spell_id))

    trainable.sort()
    indexes = _index_tables(tables)
    tick_damage = _tick_damage_index(tables, sla_spells, names, levels)

    ranks: list[SpellRank] = []
    rank_of_name: dict[str, int] = {}
    for name, level, spell_id in trainable:
        rank_of_name[name] = rank_of_name.get(name, 0) + 1
        ranks.append(_build_rank(spell_id, name, rank_of_name[name], level, indexes, tick_damage))
    return tuple(ranks)


def ranks_of(spells: Sequence[SpellRank], name: str) -> list[SpellRank]:
    """The ranks with `name`, in rank order (input is (name, rank)-sorted)."""
    return [spell for spell in spells if spell.name == name]


@dataclass(frozen=True)
class _Indexes:
    """Spell tables narrowed to DifficultyID 0 rows and indexed for O(1) lookups."""

    levels: dict[int, dict[str, str]]
    misc: dict[int, dict[str, str]]
    effects: dict[int, list[dict[str, str]]]
    cast_times: dict[int, dict[str, str]]
    durations: dict[int, dict[str, str]]
    ranges: dict[int, dict[str, str]]
    powers: dict[int, list[dict[str, str]]]        # every cost row: mana, energy, combo points
    cooldowns: dict[int, dict[str, str]]
    targets: dict[int, dict[str, str]]


def _index_tables(tables: Tables) -> _Indexes:
    """Index every join table `class_spells` needs (DifficultyID 0 rows only)."""
    effects: dict[int, list[dict[str, str]]] = {}
    for row in tables["SpellEffect"]:
        if _is_base_difficulty(row):
            effects.setdefault(int(row["SpellID"]), []).append(row)
    return _Indexes(
        levels=_by_spell(tables["SpellLevels"]),
        misc=_by_spell(tables["SpellMisc"]),
        effects=effects,
        cast_times={int(row["ID"]): row for row in tables["SpellCastTimes"]},
        durations={int(row["ID"]): row for row in tables["SpellDuration"]},
        ranges={int(row["ID"]): row for row in tables["SpellRange"]},
        powers=_all_by_spell(tables["SpellPower"]),
        cooldowns=_by_spell(tables["SpellCooldowns"]),
        targets=_by_spell(tables["SpellTargetRestrictions"]),
    )


_POWER_MANA, _POWER_ENERGY = "0", "3"   # SpellPower.PowerType (4 = combo points)
_POWER_RAGE = "1"                      # SpellPower.PowerType: warrior rage (stored in tenths)


def _all_by_spell(rows: list[dict[str, str]]) -> dict[int, list[dict[str, str]]]:
    """Every base-difficulty row per SpellID (a spell can cost energy and combo points)."""
    out: dict[int, list[dict[str, str]]] = {}
    for row in rows:
        if _is_base_difficulty(row):
            out.setdefault(int(row["SpellID"]), []).append(row)
    return out


def _by_spell(rows: list[dict[str, str]]) -> dict[int, dict[str, str]]:
    """Rows with DifficultyID 0, keyed by SpellID (the fixtures hold one row per spell)."""
    return {int(row["SpellID"]): row for row in rows if _is_base_difficulty(row)}


def _tick_damage_index(tables: Tables, sla_spells: set[int], names: dict[int, str],
                       levels: dict[int, dict[str, str]]) -> dict[tuple[str, int], tuple[float, float]]:
    """(name, BaseLevel) -> (base points, coefficient) of a tick spell's damage effect.

    A tick spell carries the tick damage of an area-triggered periodic: it shares the
    parent spell's name and BaseLevel, has an Effect == 2 row, and is not trainable.
    """
    best: dict[tuple[str, int], tuple[int, float, float]] = {}
    for row in tables["SpellEffect"]:
        if not _is_base_difficulty(row) or row["Effect"] != str(EFFECT_DAMAGE):
            continue
        spell_id = int(row["SpellID"])
        if spell_id in sla_spells:
            continue
        level_row = levels.get(spell_id)
        name = names.get(spell_id)
        if level_row is None or name is None:
            continue
        key = (name, int(_f(level_row["BaseLevel"])))
        candidate = (spell_id, _f(row["EffectBasePointsF"]), _f(row["EffectBonusCoefficient"]))
        current = best.get(key)
        if current is None or candidate[0] < current[0]:
            best[key] = candidate
    return {key: (base_points, coefficient) for key, (_, base_points, coefficient) in best.items()}


def _build_rank(spell_id: int, name: str, rank: int, level: int, indexes: _Indexes,
                tick_damage: dict[tuple[str, int], tuple[float, float]]) -> SpellRank:
    """Fill one SpellRank from the joined rows of a single spell."""
    level_row = indexes.levels[spell_id]
    misc_row = indexes.misc.get(spell_id) or {}
    effects = indexes.effects.get(spell_id, [])

    damage = next((e for e in effects if e["Effect"] == str(EFFECT_DAMAGE)), None)
    min_damage = max_damage = coefficient = damage_per_level = 0.0
    scaling_max_level = 0
    if damage is not None:
        base_points = _f(damage["EffectBasePointsF"])
        variance = _f(damage["Variance"])
        min_damage = base_points * (1 - variance / 2)
        max_damage = base_points * (1 + variance / 2)
        coefficient = _f(damage["EffectBonusCoefficient"])
        damage_per_level = _f(damage["EffectRealPointsPerLevel"])
        if damage_per_level > 0:
            scaling_max_level = int(_f(level_row["MaxLevel"]))

    channeled = bool(int(_f(misc_row.get("Attributes_1", "0"))) & _ATTR1_CHANNELED)
    mask = int(_f(misc_row.get("SchoolMask", "0")))
    schools = tuple(school for bit, school in SCHOOL_BITS if mask & bit)

    cast_time = _f(indexes.cast_times.get(int(_f(misc_row.get("CastingTimeIndex", "0"))), {}).get("Base")) / 1000.0
    # Negative bases mark shots timed by the ranged weapon (index 18: -1000000 ms); instant until
    # the ranged engine models weapon timing (#111).
    cast_time = max(0.0, cast_time)
    duration = _f(indexes.durations.get(int(_f(misc_row.get("DurationIndex", "0"))), {}).get("Duration")) / 1000.0
    range_max = _f(indexes.ranges.get(int(_f(misc_row.get("RangeIndex", "0"))), {}).get("RangeMax_0"))

    costs = {row["PowerType"]: int(_f(row["ManaCost"])) for row in indexes.powers.get(spell_id, ())}
    mana_cost = costs.get(_POWER_MANA, 0)
    energy_cost = costs.get(_POWER_ENERGY, 0)
    rage_cost = costs.get(_POWER_RAGE, 0) // 10

    cooldown_row = indexes.cooldowns.get(spell_id)
    cooldown = 0.0
    if cooldown_row is not None:
        cooldown = max(int(_f(cooldown_row["RecoveryTime"])),
                       int(_f(cooldown_row["CategoryRecoveryTime"]))) / 1000.0

    target_row = indexes.targets.get(spell_id)
    max_targets = int(_f(target_row["MaxTargets"])) if target_row is not None else 0

    slow_pct = 0.0
    for effect in effects:
        if effect["Effect"] == str(EFFECT_AURA) and effect["EffectAura"] == str(AURA_SLOW):
            slow_pct = -_f(effect["EffectBasePointsF"])
            break

    auras = {int(e["EffectAura"]) for e in effects if e["Effect"] == str(EFFECT_AURA)}
    absorb = sum(_f(e["EffectBasePointsF"]) for e in effects
                 if e["Effect"] == str(EFFECT_AURA) and int(e["EffectAura"]) in (AURA_ABSORB, AURA_MANA_SHIELD))
    immunity = duration if AURA_IMMUNITY in auras else 0.0
    # Ice Block also stuns the caster (aura 12); only count a stun on spells that aren't immunities
    stun = duration if AURA_STUN in auras and not immunity else 0.0
    root = duration if AURA_ROOT in auras else 0.0
    incapacitate = duration if AURA_TRANSFORM in auras else 0.0
    fear = duration if AURA_FEAR in auras and not incapacitate else 0.0
    disorient = duration if AURA_CONFUSE in auras and not incapacitate else 0.0
    interrupt_lockout = duration if any(e["Effect"] == str(EFFECT_INTERRUPT) for e in effects) else 0.0

    combo_row = next((e for e in effects
                      if e["Effect"] == str(EFFECT_COMBO_POINTS) and e["EffectMiscValue_0"] == "4"), None)
    combo_points = int(_f(combo_row["EffectBasePointsF"])) if combo_row is not None else 0
    per_combo_point = _f(damage["EffectPointsPerResource"]) if damage is not None else 0.0
    haste_row = next((e for e in effects
                      if e["Effect"] == str(EFFECT_AURA) and int(e["EffectAura"]) == AURA_MELEE_HASTE), None)
    haste_pct = _f(haste_row["EffectBasePointsF"]) if haste_row is not None else 0.0
    weapon_hits, weapon_bonus, weapon_normalized, weapon_pct = _weapon_strike(indexes, effects)

    periodic_damage = periodic_coefficient = tick_period = 0.0
    dot = next((e for e in effects
                if e["Effect"] == str(EFFECT_AURA) and e["EffectAura"] == str(AURA_DOT)), None)
    if dot is not None:
        tick_period = _f(dot["EffectAuraPeriod"]) / 1000.0
        ticks = _ticks(duration, tick_period)
        periodic_damage = _f(dot["EffectBasePointsF"]) * ticks
        periodic_coefficient = _f(dot["EffectBonusCoefficient"]) * ticks
    else:
        trigger = next((e for e in effects
                        if e["Effect"] == str(EFFECT_AURA)
                        and e["EffectAura"] == str(AURA_PERIODIC_TRIGGER)), None)
        if trigger is not None:
            tick_period = _f(trigger["EffectAuraPeriod"]) / 1000.0
            ticks = _ticks(duration, tick_period)
            missile = _triggered_damage(indexes, trigger)
            if missile is not None:
                periodic_damage = missile[0] * ticks
                periodic_coefficient = missile[1] * ticks
        else:
            area = next((e for e in effects
                         if e["Effect"] == str(EFFECT_AURA) and e["EffectAura"] == str(AURA_AREA_PERIODIC)), None)
            has_area_trigger = any(e["Effect"] == str(EFFECT_AREA_TRIGGER) for e in effects)
            tick = tick_damage.get((name, level)) if area is not None and has_area_trigger else None
            if tick is not None:
                tick_period = _f(area["EffectAuraPeriod"]) / 1000.0
                ticks = _ticks(duration, tick_period)
                periodic_damage = tick[0] * ticks
                periodic_coefficient = tick[1] * ticks

    return SpellRank(
        spell_id=spell_id, name=name, rank=rank, level=level, schools=schools,
        cast_time=cast_time, cooldown=cooldown, mana_cost=mana_cost, energy_cost=energy_cost,
        rage_cost=rage_cost,
        min_damage=min_damage, max_damage=max_damage, coefficient=coefficient,
        periodic_damage=periodic_damage, periodic_coefficient=periodic_coefficient,
        duration=duration, range=range_max, tick_period=tick_period,
        damage_per_level=damage_per_level, scaling_max_level=scaling_max_level,
        slow_pct=slow_pct, max_targets=max_targets, channeled=channeled,
        absorb=absorb, root=root, stun=stun, immunity=immunity, incapacitate=incapacitate,
        interrupt_lockout=interrupt_lockout, fear=fear, disorient=disorient,
        per_combo_point=per_combo_point, combo_points=combo_points, haste_pct=haste_pct,
        weapon_bonus=weapon_bonus, weapon_normalized=weapon_normalized, weapon_pct=weapon_pct,
        weapon_hits=weapon_hits,
    )


def _ticks(duration: float, tick_period: float) -> float:
    """Whole ticks that fit in `duration` at `tick_period` seconds apart."""
    if duration <= 0 or tick_period <= 0:
        return 0.0
    return float(duration // tick_period)


def _triggered_damage(indexes: _Indexes, trigger: dict[str, str]) -> tuple[float, float] | None:
    """(base points, coefficient) of the Effect == 2 row of a periodic trigger's spell.

    The triggered spell (e.g. Arcane Missile) is not in SkillLineAbility, but its
    effect rows are still in the table.
    """
    trigger_id = int(_f(trigger.get("EffectTriggerSpell", "0")))
    for effect in indexes.effects.get(trigger_id, []):
        if effect["Effect"] == str(EFFECT_DAMAGE):
            return _f(effect["EffectBasePointsF"]), _f(effect["EffectBonusCoefficient"])
    return None


def _weapon_strike(indexes: _Indexes, effects: list[dict[str, str]]) -> tuple[int, float, bool, float]:
    """(hits, bonus, normalized, pct) of the spell's weapon strikes.

    A direct strike is an Effect 121 (normalized) or 58 row of the spell itself;
    triggered strikes are Effect 64 rows whose trigger spell carries such a row
    (Mutilate strikes with main and off hand). The bonus and the Effect 31
    percentage come from the strike, or from the first triggered spell.
    """
    strike = next((e for e in effects
                   if e["Effect"] in (str(EFFECT_NORMALIZED_WEAPON), str(EFFECT_WEAPON_DAMAGE))), None)
    if strike is not None:
        strike_rows, hits = effects, 1
    else:
        strike_rows, hits = (), 0
        for effect in effects:
            if effect["Effect"] != str(EFFECT_TRIGGER_SPELL):
                continue
            rows = indexes.effects.get(int(_f(effect["EffectTriggerSpell"])), [])
            if not any(r["Effect"] in (str(EFFECT_NORMALIZED_WEAPON), str(EFFECT_WEAPON_DAMAGE)) for r in rows):
                continue
            hits += 1
            if strike is None:
                strike_rows = rows
                strike = next(r for r in rows
                              if r["Effect"] in (str(EFFECT_NORMALIZED_WEAPON), str(EFFECT_WEAPON_DAMAGE)))
    if strike is None:
        return 0, 0.0, False, 0.0
    pct_row = next((e for e in strike_rows if e["Effect"] == str(EFFECT_WEAPON_PCT)), None)
    return (hits, _f(strike["EffectBasePointsF"]), strike["Effect"] == str(EFFECT_NORMALIZED_WEAPON),
            _f(pct_row["EffectBasePointsF"]) if pct_row is not None else 0.0)


def _is_base_difficulty(row: dict[str, str]) -> bool:
    """True for DifficultyID 0 rows (or tables without a DifficultyID column)."""
    return row.get("DifficultyID", "0") == "0"


def _f(value: str | None) -> float:
    """Parse a CSV cell as a float; missing or empty cells read as 0."""
    return float(value) if value else 0.0
