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
    "Arcane Focus": (
        EffectRule("hit_chance", r"chance to hit with Arcane spells by (\d+(?:\.\d+)?)%", ("arcane",)),
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
    "Shatter": (
        EffectRule("crit_chance", r"against Frozen targets by (\d+(?:\.\d+)?)%", ("all", "@frozen")),
    ),
}

UNMODELED: dict[str, str] = {
    "Arcane Blast": "grants_spell",
    "Arcane Concentration": "proc/stack mechanic, v1",
    "Arcane Geometry": "utility: range",
    "Arcane Meditation": "resource: mana regen while casting",
    "Arcane Power": "conditional damage/mana buff, v1",
    "Arcane Resilience": "defensive: armor from intellect",
    "Arcane Shielding": "defensive: mana shield / armor",
    "Arcane Subtlety": "resistance reduction + threat, v1",
    "Improved Channeling": "proc/stack mechanic, v1",
    "Improved Counterspell": "utility: silence duration",
    "Magic Absorption": "defensive: resistances / mana restore",
    "Missile Barrage": "proc/stack mechanic, v1",
    "Presence of Mind": "conditional instant cast, v1",
    "Wand Specialization": "wand-only weapon damage",
    "Arctic Reach": "utility: range",
    "Blast Wave": "grants_spell",
    "Cold Snap": "cooldown utility",
    "Combustion": "self-buff, v1",
    "Fingers of Frost": "proc/stack mechanic, v1",
    "Flame Throwing": "utility: range",
    "Frost Warding": "defensive: ward / armor",
    "Frostbite": "control: freeze chance",
    "Heating Up": "proc/stack mechanic, v1",
    "Ice Barrier": "defensive: absorb shield",
    "Ice Block": "defensive: immunity",
    "Ice Lance": "grants_spell",
    "Improved Blizzard": "slow effect, v1",
    "Improved Fire Ward": "defensive: reflect",
    "Improved Frost Nova": "cooldown reduction",
    "Improved Scorch": "proc/stack mechanic, v1",
    "Master of Elements": "resource: mana refund on crit",
    "Permafrost": "slow/duration, v1",
    "Pyroblast": "grants_spell",
    "Wake of Fire": "cooldown + conditional crit proc, v1",
    "Winter's Chill": "proc/stack mechanic, v1",
}
