"""Mage-specific knowledge: where the Forever mage talent trees live in the client's trait data."""

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
    "Fire Power": (
        EffectRule("damage_pct", r"damage done by your Fire spells by (\d+(?:\.\d+)?)%", ("fire",)),
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
    "Wake of Fire": (
        EffectRule("cooldown", r"cooldown of your Fire Blast spell by (\d+(?:\.\d+)?) sec",
                   ("Fire Blast",), sign=-1),
    ),
    # Frost
    "Ice Shards": (
        EffectRule("crit_damage_pct",
                   r"critical strike damage bonus of your Frost spells by (\d+(?:\.\d+)?)%",
                   ("frost",)),
    ),
    "Piercing Ice": (
        EffectRule("damage_pct", r"damage done by your Frost spells by (\d+(?:\.\d+)?)%", ("frost",)),
    ),
    "Improved Frostbolt": (
        EffectRule("cast_time", r"casting time of your Frostbolt spell by (\d+(?:\.\d+)?) sec",
                   ("Frostbolt",), sign=-1),
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
    "Winter's Chill": (
        EffectRule("crit_chance",
                   r"critically hit the target by (\d+(?:\.\d+)?)% for \d+ sec\. Stacks up to (\d+) times",
                   ("Frostbolt", "Ice Lance", "@sustained"),
                   combine=lambda match: float(match.group(1)) * float(match.group(2))),
    ),
}

UNMODELED: dict[str, str] = {
    "Arcane Blast": "grants_spell",
    "Arcane Geometry": "utility: range",
    "Arcane Power": "handled in mage_rotation",
    "Arcane Resilience": "defensive: armor from intellect",
    "Arcane Shielding": "defensive: mana shield / armor",
    "Arcane Subtlety": "resistance reduction + threat, v1",
    "Improved Channeling": "proc/stack mechanic, v1",
    "Magic Absorption": "defensive: resistances / mana restore",
    "Missile Barrage": "proc/stack mechanic, v1",
    "Presence of Mind": "conditional instant cast, v1",
    "Wand Specialization": "wand-only weapon damage",
    "Arctic Reach": "utility: range",
    "Blast Wave": "grants_spell",
    "Cold Snap": "cooldown utility",
    "Combustion": "not modeled yet",
    "Flame Throwing": "utility: range",
    "Frost Warding": "defensive: ward / armor",
    "Heating Up": "handled in mage_rotation",
    "Ice Barrier": "defensive: absorb shield",
    "Ice Block": "defensive: immunity",
    "Ice Lance": "grants_spell",
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


def output(stats, spells, cls, ranks, target, *, pack=1, drink_mana_per_second=None, melee=None):
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
    best = None
    for filler in usable_fillers(char, default_params("questing", stats.level).fillers, target_level, assumptions):
        rot = rotation(char, filler, target_level=target_level, assumptions=assumptions, sustained=False)
        if rot.dps <= 0:
            continue
        value = rot.dps
        if drink_mana_per_second:
            value = rot.dps / (1 + rot.mana_per_second / drink_mana_per_second)
        if best is None or value > best[0]:
            best = (value, filler, rot)
    if best is None:
        raise ValueError(f"no mage filler available at level {stats.level}")
    _, filler, rot = best
    # once dry, the mage keeps casting at the rate combat regen pays for (as scenarios.raid's fallback)
    income = combat_regen(char, default_params("raid", stats.level))
    fallback = rot.dps * min(1.0, income / rot.mana_per_second) if rot.mana_per_second > 0 else rot.dps
    return Output(rot.dps, rot.mana_per_second, fallback, ranged=True, spell=filler.name)


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
    from wowforever.scenarios import aoe_curve, default_params, questing, raid, usable_fillers

    assumptions = Assumptions.load()
    char = _character(stats, cls.spells, cls, ranks)
    level = stats.level
    fillers = usable_fillers(char, default_params("questing", level).fillers, level, assumptions)
    duels = best_scenario_scores(char, fillers, load_kits(level=level))
    # "scenarios": which scored scenario each spell belongs to, so a description names only the
    # scenarios the build was scored in (a leveling build: questing)
    return {"kind": "mage", "scenarios": {"questing": "questing", "raid": "raid", "aoe": "aoe", "pvp": "wpvp_caster"},
            "questing": questing(char, default_params("questing", level), assumptions).details["spell"],
            "raid": raid(char, default_params("raid", level), assumptions).details["spell"],
            "aoe": aoe_curve(char, default_params("aoe", level), assumptions).details["aoe_spell"],
            "pvp": duels["wpvp_caster"]["spell"]}
