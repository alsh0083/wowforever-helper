"""Mage-specific knowledge: where the Forever mage talent trees live in the client's trait data."""

from wowforever.assumptions import Assumptions
from wowforever.classes import EffectRule, TraitLayout, TreeBand

# Forever builds its Classic-style trees on the modern Trait system (trait tree 1112 = all three
# mage trees side by side). The legacy Talent table in the client is stale and is not used.
LAYOUT = TraitLayout(
    class_name="mage",
    trait_tree_id=1112,
    trees=(
        TreeBand(tree_id=1, name="Arcane", min_x=1020),
        TreeBand(tree_id=2, name="Fire", min_x=5020),
        TreeBand(tree_id=3, name="Frost", min_x=9080),
    ),
    first_row_y=2130,
    grid=600,
)


def _fire_power(match) -> float:
    """Fire Power: a flat % before 1.60.1.70425; since, x% per Fire effect on the target up to a cap, with the
    number of effects an assumption (`fire_power_effects`, #354)."""
    if match.group(2) is None:
        return float(match.group(1))
    return min(float(match.group(1)) * Assumptions.load()["fire_power_effects"], float(match.group(2)))


# Numbers are taken from the rank text with each rule's pattern, never hard-coded;
# `sign` flips reductions. UNMODELED explains every talent not in TALENT_EFFECTS.
TALENT_EFFECTS: dict[str, tuple[EffectRule, ...]] = {
    # Arcane
    "Arcane Meditation": (
        EffectRule("regen_while_casting", r"Allows (\d+(?:\.\d+)?)% of your Mana regeneration", ("all",)),
    ),
    "Arcane Focus": (
        EffectRule("hit_chance", r"chance to hit with Arcane spells by (\d+(?:\.\d+)?)%", ("arcane",)),
    ),
    "Arcane Concentration": (
        EffectRule("mana_cost_pct",
                   r"a (\d+(?:\.\d+)?)% chance of entering a Clearcasting state",
                   ("all",), sign=-1),
    ),
    "Arcane Impact": (
        EffectRule("crit_chance", r"critical strike chance of your Arcane spells by (\d+(?:\.\d+)?)%",
                   ("arcane",)),
    ),
    "Arcane Instability": (
        EffectRule("damage_pct", r"damage done by your spells by (\d+(?:\.\d+)?)%", ("all",)),
        EffectRule("crit_chance", r"critical strike chance by (\d+(?:\.\d+)?)%", ("all",)),
    ),
    "Arcane Mind": (
        EffectRule("crit_damage_pct",
                   r"critical strike damage bonus of your Arcane spells by (\d+(?:\.\d+)?)%",
                   ("arcane",)),
    ),
    "Improved Counterspell": (
        EffectRule("control", r"Silences the target for (\d+(?:\.\d+)?) sec", ("Counterspell",)),
    ),
    # Fire
    "Critical Mass": (
        EffectRule("crit_chance", r"critical strike chance of your Fire spells by (\d+(?:\.\d+)?)%",
                   ("fire",)),
    ),
    # 1.60.1.70425: x% per Fire effect on the target, capped; how many effects is an assumption (#354)
    "Fire Power": (
        EffectRule("damage_pct",
                   r"damage done by your Fire spells by (\d+(?:\.\d+)?)%(?: per your Fire effects on the target, up to a maximum increase of (\d+(?:\.\d+)?)%)?",
                   ("fire",), combine=_fire_power),
    ),
    "Ignite": (
        EffectRule("dot_pct", r"additional (\d+(?:\.\d+)?)% of your spell", ("fire",)),
    ),
    "Improved Fireball": (
        EffectRule("cast_time",
                   r"casting time of your Fireball and Frostfire Bolt spells by (\d+(?:\.\d+)?) sec",
                   ("Fireball", "Frostfire Bolt"), sign=-1),
    ),
    "Incineration": (
        EffectRule("crit_chance", r"and Scorch spells by (\d+(?:\.\d+)?)%",
                   ("Fire Blast", "Ice Lance", "Arcane Blast", "Scorch")),
    ),
    "Improved Flamestrike": (
        EffectRule("crit_chance", r"critical strike chance of your Flamestrike spell by (\d+(?:\.\d+)?)%",
                   ("Flamestrike",)),
    ),
    "Impact": (
        EffectRule("proc_chance", r"Fire spells a (\d+(?:\.\d+)?)% chance to stun", ("fire",)),
    ),
    "Burning Soul": (
        EffectRule("pushback_pct", r"(\d+(?:\.\d+)?)% chance to not lose casting time", ("fire",)),
    ),
    "Improved Scorch": (
        EffectRule("proc_chance",
                   r"has a (\d+(?:\.\d+)?)% chance to cause your target to be vulnerable",
                   ("Scorch",)),
    ),
    "Master of Elements": (
        EffectRule("resource", r"refund (\d+(?:\.\d+)?)% of their base mana cost",
                   ("fire", "frost")),
    ),
    "Improved Fire Blast": (
        EffectRule("cooldown", r"cooldown of your Fire Blast spell by (\d+(?:\.\d+)?) sec",
                   ("Fire Blast",), sign=-1),
    ),
    # Frost
    "Ice Shards": (
        EffectRule("crit_damage_pct",
                   r"critical strike damage bonus of your Frost spells by (\d+(?:\.\d+)?)%",
                   ("frost",)),
    ),
    "Improved Frostbolt": (
        EffectRule("cast_time", r"casting time of your Frostbolt(?: and Frost Blast)? spells? by (\d+(?:\.\d+)?) sec",
                   ("Frostbolt", "Frost Blast"), sign=-1),
    ),
    "Improved Frost Nova": (
        EffectRule("cooldown", r"cooldown of your Frost Nova spell by (\d+(?:\.\d+)?) sec",
                   ("Frost Nova",), sign=-1),
    ),
    "Permafrost": (
        EffectRule("duration", r"duration of your Chill effects by (\d+(?:\.\d+)?)%", ("@chill",)),
        EffectRule("slow_pct", r"speed by an additional (\d+(?:\.\d+)?)%", ("@chill",)),
    ),
    "Improved Cone of Cold": (
        EffectRule("damage_pct", r"damage dealt by your Cone of Cold spell by (\d+(?:\.\d+)?)%",
                   ("Cone of Cold",)),
    ),
    "Elemental Precision": (
        EffectRule("hit_chance", r"chance to hit with Frost and Fire spells by (\d+(?:\.\d+)?)%",
                   ("fire", "frost")),
    ),
    "Frost Channeling": (
        EffectRule("mana_cost_pct", r"mana cost of your Frost spells by (\d+(?:\.\d+)?)%",
                   ("frost",), sign=-1),
    ),
    "Frostbite": (
        EffectRule("proc_chance", r"a (\d+(?:\.\d+)?)% chance to Freeze", ("@chill",)),
    ),
    "Fingers of Frost": (
        EffectRule("proc_chance",
                   r"effects a (\d+(?:\.\d+)?)% chance to grant you the Fingers of Frost",
                   ("@chill",)),
    ),
    "Shatter": (
        EffectRule("crit_chance", r"against Frozen targets by (\d+(?:\.\d+)?)%", ("all", "@frozen")),
    ),
    "Arcane Subtlety": (
        EffectRule("resistance_reduction", r"resistance to all your spells by (\d+(?:\.\d+)?)", ("all",)),
    ),
}

UNMODELED: dict[str, str] = {
    "Arcane Blast": "grants_spell",
    "Arcane Wrath": "grants_spell",
    "Arcane Geometry": "utility: range",
    "Arcane Power": "handled in mage_rotation",
    "Arcane Resilience": "defensive: armor from intellect",
    "Arcane Shielding": "defensive: mana shield / armor",
    "Improved Channeling": "utility: no interruption from damage; the model has no pushback (#394)",
    "Magic Absorption": "defensive: resistances / mana restore",
    "Missile Barrage": "handled in mage_rotation",
    "Presence of Mind": "handled in mage_rotation",
    "Wand Specialization": "wand-only weapon damage",
    "Arctic Reach": "utility: range",
    "Blast Wave": "grants_spell",
    "Cold Snap": "utility: resets Frost cooldowns; the single-target Frost rotation casts none (#394)",
    "Combustion": "handled in mage_rotation",
    "Flame Throwing": "utility: range",
    "Frost Warding": "defensive: ward / armor",
    "Heating Up": "handled in mage_rotation",
    "Ice Barrier": "defensive: absorb shield",
    "Ice Block": "defensive: immunity",
    "Ice Lance": "grants_spell",
    "Winter's Chill": ("damage: Cone of Cold +5% damage taken and +7% spell damage per stack, up to 5, from Frostbolt, "
                       "Frost Blast and Fingers of Frost Ice Lance (1.60.1.70685); Cone of Cold isn't in the rotations"),
    "Improved Blizzard": "slow effect, v1",
    "Improved Fire Ward": "defensive: reflect",
    "Pyroblast": "grants_spell",
}

# The calculator scores mage builds (spell damage, rotations, duels); classes without ENGINE
# get routes-only reports until the melee/ranged engine (#111).
ENGINE = True

# Mage skill lines in SkillLineAbility: Frost, Fire, Arcane.
SKILL_LINES = (6, 8, 237)


# --- class engine (#316): this module is the mage's ClassEngine ---------------------------------------
# The mage keeps its own scenario pipeline (scenarios.py) until #317; these adapters let every caller
# reach the mage through the same interface as the other classes.

def _character(stats, spells, cls, ranks):
    from wowforever.scenarios import Character

    return Character(stats.level, stats, spells, cls, dict(ranks))


def playstyle(cls, ranks) -> str:
    return "caster"


def output(stats, spells, cls, ranks, target, *, pack=1, drink_mana_per_second=None, melee=None, sustained=False):
    """The mage rotation with the filler that does the most damage per second, or with
    `drink_mana_per_second` (questing) the most per second of casting plus drinking, as the caster
    engine picks. The chosen filler is `Output.spell`."""
    from wowforever.assumptions import Assumptions
    from wowforever.classes.mage_rotation import rotation
    from wowforever.melee_scenarios import Output
    from wowforever.scenarios import combat_regen, default_params, usable_fillers

    assumptions = Assumptions.load()
    char = _character(stats, spells, cls, ranks)
    target_level = stats.level + target.level_diff
    if sustained:
        return _raid_output(char, target_level, assumptions)
    from wowforever.melee_scenarios import dungeon_pull

    p = default_params("raid", stats.level)
    income = combat_regen(char, p)
    best = None
    for filler in usable_fillers(char, default_params("questing", stats.level).fillers, target_level, assumptions):
        for n in _blast_options(char):
            rot = rotation(char, filler, target_level=target_level, assumptions=assumptions, sustained=False,
                           blast_stacks=n)
            if rot.dps <= 0:
                continue
            value = rot.dps
            if drink_mana_per_second:
                value = rot.dps / (1 + rot.mana_per_second / drink_mana_per_second)
            elif n:     # Arcane Blast stacks are worth what a 60 s pull's mana pays for (#355)
                net = rot.mana_per_second - (income - p.mana_per_second)
                value = dungeon_pull(Output(rot.dps, net, rot.dps * min(1.0, income / rot.mana_per_second)),
                                     stats.mana, stats.level)
            if best is None or value > best[0]:
                best = (value, filler, rot)
    if best is None:
        raise ValueError(f"no mage filler available at level {stats.level}")
    _, filler, rot = best
    # once dry, the mage keeps casting at the rate combat regen pays for (as scenarios.raid's fallback)
    fallback = rot.dps * min(1.0, income / rot.mana_per_second) if rot.mana_per_second > 0 else rot.dps
    return Output(rot.dps, rot.mana_per_second - (income - p.mana_per_second), fallback, ranged=True, spell=filler.name)


def aoe(stats, spells, cls, ranks, *, pack, mob_hp, armor):
    """Seconds to clear `pack` mobs with the mage's best AoE spell (scenarios.aoe_curve's model)."""
    from wowforever.assumptions import Assumptions
    from wowforever.scenarios import _best_of, _cast, default_params

    assumptions = Assumptions.load()
    char = _character(stats, spells, cls, ranks)
    spell = _best_of(char, default_params("aoe", stats.level).aoe_spells, char.level, assumptions, "AoE spell")
    ev, cast, _ = _cast(char, spell, char.level, assumptions)
    per_mob = ev / cast
    if assumptions["aoe_target_cap"] == "soft_4":
        per_mob *= min(pack, 4) / pack
    return mob_hp / per_mob, spell.name


def facts(stats, cls, ranks):
    """The spells the mage's scenarios pick at the build's level: questing, raid, AoE and caster PvP."""
    from wowforever.assumptions import Assumptions
    from wowforever.pvp.duel import best_scenario_scores, load_kits
    from wowforever.scenarios import aoe_curve, default_params, questing, raid

    assumptions = Assumptions.load()
    char = _character(stats, cls.spells, cls, ranks)
    level = stats.level
    duels = best_scenario_scores(sides(stats, cls.spells, cls, ranks), load_kits(level=level))
    # "scenarios": which scored scenario each spell belongs to, so a description names only the
    # scenarios the build was scored in (a leveling build: questing)
    return {"kind": "mage", "scenarios": {"questing": "questing", "raid": "raid", "aoe": "aoe", "pvp": "wpvp_caster"},
            "questing": questing(char, default_params("questing", level), assumptions).details["spell"],
            "raid": raid(char, default_params("raid", level), assumptions).details["spell"],
            "aoe": aoe_curve(char, default_params("aoe", level), assumptions).details["aoe_spell"],
            "pvp": duels["wpvp_caster"]["spell"]}


def duel_side(char, filler):
    """The mage's duel side with one filler: short-fight rotation DPS (no sustained buffs) plus the
    survival and control components, and Frost Nova's frozen hits against melee."""
    from wowforever.assumptions import Assumptions
    from wowforever.calc.pvp_axes import control, survival
    from wowforever.classes.mage_rotation import frozen_hit_gain, rotation
    from wowforever.pvp.duel import Side
    from wowforever.scenarios import best_rank

    s = survival(char, filler)
    c = control(char, filler)
    health = char.stats.health
    assumptions = Assumptions.load()
    nova = best_rank(char.spells, "Frost Nova", char.level)
    melee_bonus_dps = 0.0
    if nova is not None:
        improved = next((t for t in char.cls.talents if t.name == "Improved Frost Nova"), None)
        rank = char.ranks.get(improved.talent_id, 0) if improved else 0
        cut = next((e.values[rank - 1] for e in improved.effects if e.kind == "cooldown"), 0.0) if rank else 0.0
        cooldown = nova.cooldown + cut  # Improved Frost Nova's value is negative
        if cooldown > 0:
            melee_bonus_dps = frozen_hit_gain(char, filler, target_level=char.level,
                                       assumptions=assumptions) / cooldown
    rot = rotation(char, filler, target_level=char.level, assumptions=assumptions, sustained=False)
    return Side(
        health=health,
        dps=rot.dps,
        absorb_per_min=s.components["barrier"] * health,
        immunity_share=s.components["immunity"],
        root=c.components["root"],
        stun=c.components["stun"],
        slow=c.components["slow"],
        interrupt=c.components["interrupt"],
        melee_bonus_dps=melee_bonus_dps,
        root_targets=2 if nova is not None else 1,   # Frost Nova roots every nearby enemy (#287)
        pushback=s.components["pushback"],
        escapes=s.components["escapes"],
        mana=char.stats.mana,
        mana_per_second=rot.mana_per_second,
    )


def sides(stats, spells, cls, ranks):
    """The mage's duel sides, one per usable filler: each duel scenario takes the best (#97)."""
    from wowforever.assumptions import Assumptions
    from wowforever.scenarios import default_params, usable_fillers

    char = _character(stats, spells, cls, ranks)
    fillers = usable_fillers(char, default_params("questing", stats.level).fillers, stats.level, Assumptions.load())
    return [(filler.name, duel_side(char, filler)) for filler in fillers]


def _blast_options(char) -> range:
    """Arcane Blast stack counts to try per buff window: 0 to its max once learned (1.60.1.70425, #355), else 0."""
    from wowforever.classes.mage_rotation import arcane_blast_stacks
    from wowforever.scenarios import best_rank

    stacks = arcane_blast_stacks(char.cls)
    if stacks is None or best_rank(char.spells, "Arcane Blast", char.level) is None:
        return range(1)
    return range(stacks[2] + 1)


def _raid_output(char, target_level, assumptions):
    """The mage's raid Output (#317, part A): the sustained rotation of the filler with the best
    shared-raid score, Evocation as the mana cooldown, and once dry the fallback that tries every
    filler rank at the rate combat regen pays for (scenarios.raid's model)."""
    from wowforever.classes.mage_rotation import rotation
    from wowforever.melee_scenarios import Output, raid_dps
    from wowforever.scenarios import _fallback, combat_regen, default_params, spirit_regen, usable_fillers

    p = default_params("raid", char.level)
    income = combat_regen(char, p)
    evocation = ((p.evocation_seconds,
                  spirit_regen(char.stats) * (1 + p.evocation_regen_pct / 100) * p.evocation_seconds)
                 if p.evocation else None)
    best = None
    for filler in usable_fillers(char, p.fillers, target_level, assumptions):
        fallback = None
        for n in _blast_options(char):      # Arcane Blast stacks per buff window, picked by the raid's budget (#355)
            rot = rotation(char, filler, target_level=target_level, assumptions=assumptions, sustained=True,
                           blast_stacks=n)
            if fallback is None:
                fallback = (_fallback(char, p, filler, target_level, assumptions, income)[0]
                            if p.fallback and rot.mana_per_second > income else 0.0)
            out = Output(rot.dps, rot.mana_per_second - (income - p.mana_per_second), fallback,
                         ranged=True, spell=filler.name, mana_cooldown=evocation)
            score = raid_dps(out, char.stats.mana, p)
            if best is None or score > best[0]:
                best = (score, out)
    if best is None:
        raise ValueError(f"no mage filler available at level {char.level}")
    return best[1]
