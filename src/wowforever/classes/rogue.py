"""Rogue-specific knowledge: where the Forever rogue talent trees live in the client's trait data.

Stage 2 of the alts (#131 part 2): the damage talents carry effect rules read from the rank
text; the rest stay classified but unmodeled until the alts-engine milestone (#111).
"""

from wowforever.classes import EffectRule, TraitLayout, TreeBand

# Trait tree 1111 holds all three rogue trees side by side, on the same grid as the mage's 1112.
LAYOUT = TraitLayout(
    class_name="rogue",
    trait_tree_id=1111,
    trees=(
        TreeBand(tree_id=1, name="Assassination", min_x=1020),
        TreeBand(tree_id=2, name="Combat", min_x=5020),
        TreeBand(tree_id=3, name="Subtlety", min_x=9080),
    ),
    first_row_y=2130,
    grid=600,
)

# Numbers are taken from the rank text with each rule's pattern, never hard-coded;
# `sign` flips reductions. UNMODELED explains every talent not in TALENT_EFFECTS.
TALENT_EFFECTS: dict[str, tuple[EffectRule, ...]] = {
    # Assassination
    "Malice": (
        EffectRule("crit_chance",
                   r"critical strike chance with all attacks and Poisons by (\d+(?:\.\d+)?)%",
                   ("all",)),
    ),
    "Ruthlessness": (
        EffectRule("proc_chance", r"a (\d+(?:\.\d+)?)% chance to add a Combo Point",
                   ("@finisher",)),
    ),
    "Murder": (
        EffectRule("damage_pct", r"damage dealt by (\d+(?:\.\d+)?)%", ("@humanoid",)),
    ),
    "Improved Slice and Dice": (
        EffectRule("duration",
                   r"duration of your Slice and Dice ability by (\d+(?:\.\d+)?)%",
                   ("Slice and Dice",)),
    ),
    "Relentless Strikes": (
        EffectRule("resource", r"have a (\d+(?:\.\d+)?)% chance per Combo Point", ("@finisher",)),
    ),
    "Lethality": (
        EffectRule("crit_damage_pct",
                   r"critical strike damage bonus of your .* by (\d+(?:\.\d+)?)%",
                   ("Sinister Strike", "Gouge", "Backstab", "Mutilate", "Ghostly Strike",
                    "Hemorrhage")),
    ),
    "Vile Poisons": (
        EffectRule("damage_pct", r"damage dealt by your poisons by (\d+(?:\.\d+)?)%",
                   ("@poison",)),
    ),
    "Seal Fate": (
        EffectRule("proc_chance",
                   r"a (\d+(?:\.\d+)?)% chance to add an additional Combo Point",
                   ("@builder_crit",)),
    ),
    # Combat
    "Improved Eviscerate": (
        EffectRule("damage_pct", r"Eviscerate ability by (\d+(?:\.\d+)?)%", ("Eviscerate",)),
    ),
    "Improved Sinister Strike": (
        EffectRule("energy_cost",
                   r"Energy cost of your Sinister Strike ability by (\d+(?:\.\d+)?)",
                   ("Sinister Strike",), sign=-1),
    ),
    "Puncturing Wounds": (
        EffectRule("crit_chance",
                   r"critical strike chance of your Backstab by (\d+(?:\.\d+)?)%",
                   ("Backstab",)),
        EffectRule("crit_chance", r"Mutilate by (\d+(?:\.\d+)?)%", ("Mutilate",)),
        EffectRule("proc_chance", r"gives Backstab a (\d+(?:\.\d+)?)% chance",
                   ("@backstab_combo",)),
    ),
    "Precision": (
        EffectRule("hit_chance", r"chance to hit by (\d+(?:\.\d+)?)%", ("all",)),
    ),
    "Dual Wield Specialization": (
        EffectRule("damage_pct", r"off-hand weapon by (\d+(?:\.\d+)?)%", ("@off_hand",)),
    ),
    "Weapon Expertise": (
        EffectRule("dodge_reduction", r"Dodged or Parried by (\d+(?:\.\d+)?)%", ("all",)),
    ),
    "Aggression": (
        EffectRule("damage_pct", r"damage of your .* abilities by (\d+(?:\.\d+)?)%",
                   ("Sinister Strike", "Backstab", "Eviscerate")),
    ),
    # Subtlety
    "Opportunity": (
        EffectRule("damage_pct", r"damage dealt by your .* abilities by (\d+(?:\.\d+)?)%",
                   ("Backstab", "Garrote", "Ambush", "Mutilate")),
    ),
    "Improved Ambush": (
        EffectRule("crit_chance", r"Ambush ability by (\d+(?:\.\d+)?)%", ("Ambush",)),
    ),
    "Serrated Blades": (
        EffectRule("armor_pen", r"ignore (\d+(?:\.\d+)?)% of your target's Armor", ("all",)),
    ),
}

# Every rogue talent, with why it is not modeled yet. "grants_spell" marks talents that teach an
# activated ability; the rest get "<category>: <what it does>".
UNMODELED: dict[str, str] = {
    # Assassination
    "Improved Gouge": "control: longer Gouge duration",
    "Remorseless Attacks": "melee damage: post-kill crit buff on core abilities (#111)",
    "Improved Expose Armor": "resource: cheaper Expose Armor, refunds Combo Points",
    "Cold Blood": "grants_spell",
    "Improved Poisons": "poison: better apply chance, charge savings",
    "Vigor": "resource: +10 maximum Energy",
    "Mutilate": "grants_spell",
    "Improved Kidney Shot": "control: more damage to Kidney Shot stuns",
    "Venom": "grants_spell",
    # Combat
    "Lightning Reflexes": "defensive: +5% Dodge chance",
    "Deflection": "defensive: +6% Parry chance",
    "Endurance": "utility: shorter Sprint and Evasion cooldowns",
    "Riposte": "grants_spell",
    "Improved Sprint": "mobility: Sprint cleanses movement impairments",
    "Improved Kick": "control: Kick silences the target",
    "Flawless Execution": "resource: cheaper Eviscerate",
    "Blade Flurry": "grants_spell",
    "Hack and Slash": "proc: weapon-based extra attack chance",
    "Adrenaline Rush": "grants_spell",
    # Subtlety
    "Camouflage": "stealth: faster Stealth, shorter cooldown",
    "Master of Deception": "stealth: harder to detect while Stealthed",
    "Setup": "resource: Combo Point after dodges or resisted spells",
    "Elusiveness": "utility: shorter Vanish and Blind cooldowns",
    "Dirty Tricks": "resource: cheaper Sap and Blind",
    "Initiative": "resource: extra Combo Point from Ambush/Garrote/Cheap Shot",
    "Ghostly Strike": "grants_spell",
    "Improved Distract": "utility: larger Distract radius, less detection of distracted enemies",
    "Heightened Senses": "stealth: better Stealth detection, less hit by spells and ranged",
    "Premeditation": "grants_spell",
    "Dirty Deeds": "stealth: cheaper openers, Garrote works from the front",
    "Preparation": "grants_spell",
    "Hemorrhage": "grants_spell",
    "Quietus": "melee damage: +10% damage vs targets below 35% health (#111)",
    "Cutthroat": "stealth: Backstab can enable Ambush without Stealth",
    "Thousand Cuts": "resource: Rupture ticks reduce Hemorrhage/Backstab Energy cost",
}

# Two-tree builds the community actually plays (#104): Subtlety Preparation is 16/12/23.
HYBRIDS = ("Assassination/Subtlety",)

# Rogue skill lines in SkillLineAbility: Assassination, Combat, Subtlety, Poisons.
SKILL_LINES = (253, 38, 39, 40)
