"""Priest-specific knowledge: where the Forever priest talent trees live in the client's trait data.

Stage 1 of class-specific opponents (#34, #152): the trees and spells load and every talent is
classified; nothing is modeled yet. The priest is an opponent, not a dashboard class.
"""

from wowforever.classes import EffectRule, TraitLayout, TreeBand

# Trait tree 1114 holds all three priest trees side by side, on the same grid as the mage's 1112.
LAYOUT = TraitLayout(
    class_name="priest",
    trait_tree_id=1114,
    trees=(
        TreeBand(tree_id=1, name="Discipline", min_x=1020),
        TreeBand(tree_id=2, name="Holy", min_x=5020),
        TreeBand(tree_id=3, name="Shadow", min_x=9080),
    ),
    first_row_y=2130,
    grid=600,
    # A second Holy Specialization node (105865) is parked at Y 21300, off the talent UI.
    hidden_nodes=frozenset({105865}),
)

TALENT_EFFECTS: dict[str, tuple[EffectRule, ...]] = {}

# Every priest talent, with why it isn't modeled.
UNMODELED: dict[str, str] = {
    # Discipline
    "Power in Light": "damage: Smite and Penance vs Holy Fire targets",
    "Wand Specialization": "damage: +25% wand damage",
    "Twin Disciplines": "damage: +5% instant spell damage and healing",
    "Silent Resolve": "defensive: shorter stuns, fears and silences, less threat",
    "Holy Precision": "damage: +18% Holy spell hit",
    "Improved Power Word: Shield": "defensive: stronger Power Word: Shield",
    "Martyrdom": "defensive: pushback immunity after being crit",
    "Mental Agility": "resource: cheaper Smite, Holy Fire and instants",
    "Inner Focus": "grants_spell",
    "Meditation": "resource: 50% mana regeneration while casting",
    "Improved Inner Fire": "defensive: stronger Inner Fire",
    "Mental Strength": "buff: +15% Intellect",
    "Soul Warding": "defensive: faster, cheaper Power Word: Shield",
    "Improved Mana Burn": "resource: faster Mana Burn",
    "Penance": "grants_spell",
    "Renewed Hope": "healing: heal crit",
    "Divine Aegis": "healing: crit heals leave a shield",
    "Power Infusion": "grants_spell",
    # Holy
    "Twilight Focus": "utility: 70% pushback avoidance",
    "Improved Renew": "healing: +15% Renew",
    "Holy Specialization": "damage: +5% Holy crit",
    "Spell Warding": "defensive: 10% less spell damage taken",
    "Divine Fury": "damage: faster Smite, Holy Fire and heals",
    "Holy Nova": "grants_spell",
    "Blessed Recovery": "defensive: heal after big hits",
    "Inspiration": "healing: crit heals raise target armor",
    "Holy Reach": "utility: Smite, Holy Fire and Holy Nova range",
    "Improved Healing": "resource: cheaper heals",
    "Searing Light": "damage: +5% Holy damage",
    "Binding Heal": "grants_spell",
    "Litany of Light": "resource: mana back when alternating heals",
    "Spirit of Redemption": "healing: keep healing after death",
    "Spiritual Guidance": "healing: spell power from Spirit",
    "Spiritual Healing": "healing: +10% healing",
    "Prayer of Mending": "grants_spell",
    # Shadow
    "Shadow Focus": "damage: +5% Shadow hit",
    "Blackout": "control: Shadow spells can stun 3 s",
    "Spirit Tap": "resource: Spirit after kills",
    "Shadow Affinity": "threat: less Shadow threat",
    "Improved Shadow Word: Pain": "damage: longer Shadow Word: Pain",
    "Shadow Reach": "utility: +20% Shadow range",
    "Improved Mind Blast": "damage: Mind Blast cooldown -2.5 s",
    "Improved Psychic Scream": "control: Psychic Scream cooldown -4 s",
    "Mind Flay": "grants_spell",
    "Improved Mind Flay": "damage: Mind Flay damage, range and slow",
    "Improved Fade": "defensive: Fade cooldown -6 s",
    "Vampiric Embrace": "grants_spell",
    "Shadow Weaving": "damage: stacking Shadow damage",
    "Silence": "grants_spell",
    "Devouring Contagion": "damage: cheaper, spreading Devouring Plague",
    "Early Demise": "damage: Shadow Word: Death crit below 20%",
    "Darkness": "damage: +10% Shadow damage",
    "Shadowform": "grants_spell",
}

# Priest skill lines in SkillLineAbility: Discipline, Holy, Shadow.
SKILL_LINES = (613, 56, 78)

# Shown on the dashboard while the class is routes-only (planning round 2, Q2/Q3).
SCORING_NOTE = "Shadow scores come with the caster spell engine (#163, #164); Discipline and Holy healing stay unscored."
