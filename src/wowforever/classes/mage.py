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

# Mage skill lines in SkillLineAbility: Frost, Fire, Arcane.
SKILL_LINES = (6, 8, 237)
