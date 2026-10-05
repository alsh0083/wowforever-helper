"""Druid-specific knowledge: where the Forever druid talent trees live in the client's trait data.

Stage 1 of class-specific opponents (#34, #152): the trees and spells load and every talent is
classified; nothing is modeled yet. The druid is an opponent, not a dashboard class.
"""

from wowforever.classes import EffectRule, TraitLayout, TreeBand

# Trait tree 1089 holds all three druid trees side by side, on the same grid as the mage's 1112.
LAYOUT = TraitLayout(
    class_name="druid",
    trait_tree_id=1089,
    trees=(
        TreeBand(tree_id=1, name="Balance", min_x=1020),
        TreeBand(tree_id=2, name="Feral Combat", min_x=5020),
        TreeBand(tree_id=3, name="Restoration", min_x=9080),
    ),
    first_row_y=2130,
    grid=600,
)

TALENT_EFFECTS: dict[str, tuple[EffectRule, ...]] = {}

# Every druid talent, with why it isn't modeled.
UNMODELED: dict[str, str] = {
    # Balance
    "Improved Wrath": "damage: faster, cheaper Wrath",
    "Genesis": "damage: +5% periodic damage and healing",
    "Moonglow": "resource: damaging spells cost 25% less mana",
    "Improved Moonfire": "damage: Moonfire damage and crit",
    "Nature's Majesty": "damage: +4% spell and melee crit",
    "Nature's Reach": "damage: Balance spell range and hit",
    "Improved Entangling Roots": "control: stronger Entangling Roots",
    "Nature's Splendor": "damage: longer Moonfire, Rejuvenation, Regrowth, Insect Swarm",
    "Insect Swarm": "grants_spell",
    "Vengeance": "damage: Arcane and Nature crit damage",
    "Improved Starfire": "control: faster Starfire that can stun 3 s",
    "Overgrowth": "control: Entangling Roots on 2 more targets",
    "Nature's Grace": "proc: spell crits speed up the next cast",
    "Eclipse": "proc: Wrath speeds up Starfire",
    "Moonfury": "damage: +10% Arcane and Nature damage",
    "Moonkin Form": "grants_spell",
    # Feral Combat
    "Ferocity": "resource: feral abilities cost 5 less Rage or Energy",
    "Heart of the Wild": "buff: +10% Intellect, bear Stamina",
    "Feral Swiftness": "mobility: Cat Form speed and dodge",
    "Feral Instinct": "damage: Swipe damage, stealthier Prowl",
    "Brutal Impact": "control: longer Bash and Pounce stuns",
    "Thick Hide": "defensive: more armor in forms",
    "Shredding Attacks": "resource: cheaper Shred and Lacerate",
    "Savage Fury": "damage: +10% feral ability damage",
    "Feral Charge": "grants_spell",
    "Sharpened Claws": "damage: +6% crit in forms",
    "Shifting Power": "grants_spell",
    "Primal Bite": "grants_spell",
    "Predatory Strikes": "damage: attack power in forms",
    "Blood Frenzy": "resource: Rage on bear crits",
    "Improved Shifting Power": "resource: Shifting Power cooldown -8 s",
    "Leader of the Pack": "buff: party melee crit aura",
    "Predatory Instincts": "damage: +20% melee crit damage",
    "Natural Reaction": "defensive: +5% dodge, Rage on dodge",
    "Rend and Tear": "damage: +10% vs bleeding targets",
    "Berserk": "damage: Primal Bite cleaves and crits more",
    # Restoration
    "Nature's Focus": "utility: 70% pushback avoidance",
    "Furor": "resource: Rage or Energy on shapeshift",
    "Naturalist": "damage: +5% damage, faster Healing Touch",
    "Subtlety": "threat: less threat from Nature and Arcane spells",
    "Natural Shapeshifter": "resource: cheaper shapeshifting",
    "Reflection": "resource: 50% mana regeneration while casting",
    "Gift of Nature": "healing: +10% healing",
    "Gift of the Earthmother": "healing: shorter global cooldown on heals",
    "Tranquil Spirit": "resource: cheaper Healing Touch and Tranquility",
    "Improved Rejuvenation": "healing: +15% Rejuvenation",
    "Swiftmend": "grants_spell",
    "Nature's Swiftness": "grants_spell",
    "Living Spirit": "buff: +15% Spirit",
    "Improved Tranquility": "healing: Tranquility cooldown and threat",
    "Improved Regrowth": "healing: Regrowth crit",
    "Wild Growth": "grants_spell",
}

# Druid skill lines in SkillLineAbility: Balance, Feral Combat, Restoration.
SKILL_LINES = (574, 134, 573)
