"""Warlock-specific knowledge: where the Forever warlock talent trees live in the client's trait data.

Stage 1 of class-specific opponents (#34, #152): the trees and spells load and every talent is
classified; nothing is modeled yet. The warlock is an opponent, not a dashboard class.
"""

from wowforever.classes import EffectRule, TraitLayout, TreeBand

# Trait tree 1116 holds all three warlock trees side by side, on the same grid as the mage's 1112.
LAYOUT = TraitLayout(
    class_name="warlock",
    trait_tree_id=1116,
    trees=(
        TreeBand(tree_id=1, name="Affliction", min_x=1020),
        TreeBand(tree_id=2, name="Demonology", min_x=5020),
        TreeBand(tree_id=3, name="Destruction", min_x=9080),
    ),
    first_row_y=2130,
    grid=600,
    # Amplify Curse and Improved Life Tap sit 10 units off their grid row.
    snap=20,
)

TALENT_EFFECTS: dict[str, tuple[EffectRule, ...]] = {}

# Every warlock talent, with why it isn't modeled.
UNMODELED: dict[str, str] = {
    # Affliction
    "Improved Life Tap": "resource: +20% Life Tap mana",
    "Suppression": "damage: +5% hit, less threat",
    "Improved Corruption": "damage: instant, stronger Corruption",
    "Malediction": "damage: +5% periodic damage",
    "Soul Harvest": "resource: mana regeneration after Drain Soul kills",
    "Improved Drains": "damage: +20% drains",
    "Improved Bane of Agony": "damage: +10% Bane of Agony",
    "Fel Concentration": "utility: drains resist pushback",
    "Amplify Curse": "control: stronger next curse",
    "Pandemic": "damage: periodic crit damage",
    "Malevolence": "damage: +5% Shadow crit",
    "Nightfall": "proc: Shadow Trance from drains and Corruption",
    "Curse of Exhaustion": "grants_spell",
    "Siphon Life": "grants_spell",
    "Soul Siphon": "damage: drains scale with afflictions",
    "Shadow Mastery": "damage: +5% Shadow damage",
    "Wrack": "grants_spell",
    # Demonology
    "Improved Health Funnel": "pet: stronger Health Funnel",
    "Improved Imp": "pet: stronger Imp",
    "Demonic Embrace": "defensive: +15% Stamina",
    "Unholy Power": "pet: +10% pet damage",
    "Demonic Aegis": "defensive: stronger Demon Skin and Demon Armor",
    "Improved Voidwalker": "pet: stronger Voidwalker",
    "Fel Vitality": "pet: pet health and mana",
    "Demonic Energies": "pet: heal pet from spell damage",
    "Improved Sayaad": "pet: stronger Succubus and Incubus",
    "Demonic Sacrifice": "grants_spell",
    "Master Summoner": "pet: faster pet summons",
    "Decimation": "damage: Soul Fire cooldown and execute",
    "Fel Domination": "grants_spell",
    "Demonic Brand": "pet: pet bonus vs branded targets",
    "Improved Felhunter": "pet: stronger Felhunter",
    "Soul Link": "grants_spell",
    "Demonic Knowledge": "damage: spell damage with a demon out",
    "Master Demonologist": "pet: bonus per active demon",
    "Demonic Pact": "pet: Demonic Sacrifice persists",
    # Destruction
    "Destructive Reach": "utility: +20% spell range",
    "Improved Shadow Bolt": "damage: Shadow Bolt crits raise Shadow damage taken",
    "Bane": "damage: faster Shadow Bolt, Immolate, Incinerate, Soul Fire",
    "Molten Skin": "defensive: 10% less damage taken",
    "Cataclysm": "resource: cheaper Destruction spells",
    "Aftermath": "control: Conflagrate dazes, stronger Immolate",
    "Ruin": "damage: Destruction crit damage",
    "Shadowburn": "grants_spell",
    "Intensity": "utility: Destruction spells resist pushback",
    "Agonizing Flames": "damage: Searing Pain crit, Destruction damage",
    "Conflagrate": "grants_spell",
    "Pyroclasm": "control: Soul Fire and AoE can stun",
    "Bane of Havoc": "grants_spell",
    "Fire and Brimstone": "damage: Conflagrate crit",
    "Shadow and Flame": "damage: Conflagrate raises Shadow and Fire damage",
    "Incinerate": "grants_spell",
}

# Warlock skill lines in SkillLineAbility: Affliction, Demonology, Destruction.
SKILL_LINES = (355, 354, 593)

# Shown on the dashboard while the class is routes-only (planning round 2, Q2/Q3).
SCORING_NOTE = "Scores come with the caster spell engine (#163, #165)."
