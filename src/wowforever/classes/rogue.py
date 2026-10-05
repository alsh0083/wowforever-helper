"""Rogue-specific knowledge: where the Forever rogue talent trees live in the client's trait data.

Stage 1 of the alts (#103): the trees and spells load, and every talent is classified. Melee
damage is not modeled until the alts-engine milestone (#111), so no talent has effect rules yet.
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

TALENT_EFFECTS: dict[str, tuple[EffectRule, ...]] = {}

# Every rogue talent, with why it is not modeled yet. "grants_spell" marks talents that teach an
# activated ability; the rest get "<category>: <what it does>".
UNMODELED: dict[str, str] = {
    # Assassination
    "Improved Gouge": "control: longer Gouge duration",
    "Remorseless Attacks": "melee damage: post-kill crit buff on core abilities (#111)",
    "Malice": "melee damage: crit chance with attacks and Poisons (#111)",
    "Ruthlessness": "resource: finishing moves add a Combo Point on a chance",
    "Murder": "melee damage: +4% damage vs Humanoid and Giant (#111)",
    "Improved Slice and Dice": "melee damage: longer Slice and Dice duration (#111)",
    "Relentless Strikes": "resource: finishing moves restore Energy",
    "Improved Expose Armor": "resource: cheaper Expose Armor, refunds Combo Points",
    "Lethality": "melee damage: crit damage bonus on core abilities (#111)",
    "Vile Poisons": "poison: +20% poison damage, dispel resistance",
    "Cold Blood": "grants_spell",
    "Improved Poisons": "poison: better apply chance, charge savings",
    "Vigor": "resource: +10 maximum Energy",
    "Mutilate": "grants_spell",
    "Improved Kidney Shot": "control: more damage to Kidney Shot stuns",
    "Seal Fate": "resource: crits add an extra Combo Point",
    "Venom": "grants_spell",
    # Combat
    "Improved Eviscerate": "melee damage: +20% Eviscerate damage (#111)",
    "Improved Sinister Strike": "resource: cheaper Sinister Strike",
    "Lightning Reflexes": "defensive: +5% Dodge chance",
    "Puncturing Wounds": "melee damage: Backstab/Mutilate crit, extra Combo Point chance (#111)",
    "Deflection": "defensive: +6% Parry chance",
    "Precision": "melee damage: +3% chance to hit (#111)",
    "Endurance": "utility: shorter Sprint and Evasion cooldowns",
    "Riposte": "grants_spell",
    "Improved Sprint": "mobility: Sprint cleanses movement impairments",
    "Improved Kick": "control: Kick silences the target",
    "Flawless Execution": "resource: cheaper Eviscerate",
    "Dual Wield Specialization": "melee damage: +25% off-hand weapon damage (#111)",
    "Blade Flurry": "grants_spell",
    "Hack and Slash": "proc: weapon-based extra attack chance",
    "Weapon Expertise": "melee damage: attacks less Dodged or Parried (#111)",
    "Aggression": "melee damage: +6% core ability damage (#111)",
    "Adrenaline Rush": "grants_spell",
    # Subtlety
    "Camouflage": "stealth: faster Stealth, shorter cooldown",
    "Master of Deception": "stealth: harder to detect while Stealthed",
    "Opportunity": "melee damage: +10% Backstab/Garrote/Ambush/Mutilate damage (#111)",
    "Setup": "resource: Combo Point after dodges or resisted spells",
    "Elusiveness": "utility: shorter Vanish and Blind cooldowns",
    "Dirty Tricks": "resource: cheaper Sap and Blind",
    "Improved Ambush": "melee damage: +45% Ambush crit (#111)",
    "Initiative": "resource: extra Combo Point from Ambush/Garrote/Cheap Shot",
    "Ghostly Strike": "grants_spell",
    "Improved Distract": "utility: larger Distract radius, less detection of distracted enemies",
    "Heightened Senses": "stealth: better Stealth detection, less hit by spells and ranged",
    "Premeditation": "grants_spell",
    "Serrated Blades": "melee damage: armor penetration, +30% Rupture damage (#111)",
    "Dirty Deeds": "stealth: cheaper openers, Garrote works from the front",
    "Preparation": "grants_spell",
    "Hemorrhage": "grants_spell",
    "Quietus": "melee damage: +10% damage vs targets below 35% health (#111)",
    "Cutthroat": "stealth: Backstab can enable Ambush without Stealth",
    "Thousand Cuts": "resource: Rupture ticks reduce Hemorrhage/Backstab Energy cost",
}

# Rogue skill lines in SkillLineAbility: Assassination, Combat, Subtlety, Poisons.
SKILL_LINES = (253, 38, 39, 40)
