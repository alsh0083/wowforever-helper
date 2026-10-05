"""Paladin-specific knowledge: where the Forever paladin talent trees live in the client's trait data.

Stage 1 of class-specific opponents (#34, #152): the trees and spells load and every talent is
classified; nothing is modeled yet. The paladin is an opponent, not a dashboard class.
"""

from wowforever.classes import EffectRule, TraitLayout, TreeBand

# Trait tree 1100 holds all three paladin trees side by side, on the same grid as the mage's 1112.
LAYOUT = TraitLayout(
    class_name="paladin",
    trait_tree_id=1100,
    trees=(
        TreeBand(tree_id=1, name="Holy", min_x=1020),
        TreeBand(tree_id=2, name="Protection", min_x=5020),
        TreeBand(tree_id=3, name="Retribution", min_x=9080),
    ),
    first_row_y=2130,
    grid=600,
    # Improved Seal of Fury and Swift Judgement sit 10 units right of their grid column.
    snap=20,
)

TALENT_EFFECTS: dict[str, tuple[EffectRule, ...]] = {}

# Every paladin talent, with why it isn't modeled.
UNMODELED: dict[str, str] = {
    # Holy
    "Divine Strength": "buff: +10% Strength",
    "Divine Intellect": "buff: +10% Intellect",
    "Healing Light": "healing: +12% Holy Light, Flash of Light, Holy Shock",
    "Spiritual Focus": "utility: heals resist pushback",
    "Improved Seals": "damage: +15% Seal and Judgement damage",
    "Unyielding Faith": "defensive: shorter Fear and Disorient",
    "Voice of Truth": "defensive: immune to Silence and Interrupt for 6 s",
    "Reverence": "resource: 30% mana regeneration while casting",
    "Purifying Power": "resource: cheaper Cleanse, shorter Exorcism and Holy Wrath cooldowns",
    "Infusion of Light": "proc: crits speed up the next Holy Light",
    "Illumination": "proc: heal crits refund mana",
    "Divine Favor": "grants_spell",
    "Divine Precision": "damage: +18% Holy spell hit",
    "Holy Shock": "grants_spell",
    "Consecrated Ground": "damage: Holy damage vs enemies entering Consecration",
    "Holy Power": "damage: Holy Shock, Holy Strike and spell crit",
    "Light's Vigil": "grants_spell",
    # Protection
    "Toughness": "defensive: +10% armor from items",
    "Redoubt": "defensive: block chance after being hit",
    "Precision": "damage: +3% hit",
    "Guardian's Favor": "utility: Blessing of Protection and Freedom",
    "Anticipation": "defensive: +20 Defense",
    "Improved Seal of Fury": "resource: mana when Seal of Fury's shield breaks",
    "Improved Righteous Fury": "defensive: 6% less damage taken in Righteous Fury",
    "Shield Specialization": "defensive: stronger shield blocks that restore mana",
    "Sacred Duty": "defensive: Stamina, shorter Divine Shield cooldowns",
    "Swift Judgement": "grants_spell",
    "One-Handed Weapon Specialization": "damage: +10% one-handed damage",
    "Improved Hammer of Justice": "control: Hammer of Justice cooldown -15 s",
    "Templar's Bulwark": "grants_spell",
    "Reckoning": "proc: extra attacks after blocking",
    "Iron Creed": "threat: Holy Strike threat",
    "Holy Shield": "grants_spell",
    # Retribution
    "Deflection": "defensive: +5% parry",
    "Benediction": "resource: instant spells cost 10% less mana",
    "Improved Judgement": "damage: Judgement cooldown -2 s",
    "Holy Conduit": "resource: cheaper Consecration, Holy Wrath, Exorcism, Hammer of Wrath",
    "Conviction": "damage: +5% melee crit",
    "Vindication": "proc: melee hits lower enemy attack power",
    "Sanctified Judgement": "resource: Judgement refunds seal mana",
    "Seal of Command": "grants_spell",
    "Pursuit of Justice": "mobility: +15% movement speed",
    "Eye for an Eye": "damage: reflects crit damage",
    "Sacred Arbiter": "damage: Holy Strike damage, refreshes Judgements",
    "Two-Handed Weapon Specialization": "damage: +6% two-handed damage",
    "Vengeance": "damage: Physical and Holy damage after crits",
    "Repentance": "grants_spell",
    "Champion of the Light": "damage: spell damage from Intellect",
    "Instrument of Law": "damage: faster Hammer of Wrath, less threat",
    "Twist of Light": "resource: cheaper Seals, echo on seal swap",
}

# Paladin skill lines in SkillLineAbility: Holy, Protection, Retribution.
SKILL_LINES = (594, 267, 184)
