"""Warrior-specific knowledge: where the Forever warrior talent trees live in the client's trait data.

Stage 1 of class-specific opponents (#34, #149): the trees and spells load and every talent is
classified; nothing is modeled yet. The warrior is an opponent, not a dashboard class.
"""

from wowforever.classes import EffectRule, TraitLayout, TreeBand

# Trait tree 1117 holds all three warrior trees side by side, on the same grid as the mage's 1112.
LAYOUT = TraitLayout(
    class_name="warrior",
    trait_tree_id=1117,
    trees=(
        TreeBand(tree_id=1, name="Arms", min_x=1020),
        TreeBand(tree_id=2, name="Fury", min_x=5020),
        TreeBand(tree_id=3, name="Protection", min_x=9080),
    ),
    first_row_y=2130,
    grid=600,
)

TALENT_EFFECTS: dict[str, tuple[EffectRule, ...]] = {}

# Every warrior talent, with why it isn't modeled. Talents marked "(no rank text)" are
# classified from the name: wowforevertalent.com is a build behind the client for them.
UNMODELED: dict[str, str] = {
    # Arms
    "Improved Heroic Strike": "rage: Heroic Strike costs 3 less Rage",
    "Deflection": "defensive: +5% parry",
    "Improved Rend": "melee damage: Rend bleeds 35% harder",
    "Improved Charge": "rage: Charge generates 6 more Rage",
    "Improved Tactical Mastery": "rage: keep 15 more Rage on stance change",
    "Improved Overpower": "melee damage: Overpower +50% crit",
    "Anger Management": "rage: 1 Rage every 3 s in combat",
    "Deep Wounds": "melee damage: crits bleed for 60% of weapon damage",
    "Spearing Strike": "grants_spell",
    "Two-Handed Weapon Specialization": "melee damage: +3% two-handed damage",
    "Impale": "melee damage: +20% ability crit damage",
    "Bloodthrill": "proc: main-hand hits on Rend targets can enable an ability",
    "Sweeping Strikes": "grants_spell",
    "Weaponmaster": "melee damage: weapon-type bonus (crit, damage)",
    "Improved Slam": "melee damage: faster Slam that doesn't reset swings",
    "Improved Hamstring": "control: Hamstring has 15% chance to root 5 s",
    "Mortal Strike": "grants_spell",
    # Fury
    "Booming Voice": "shout: shouts reach 50% farther and cost 25% less",
    "Cruelty": "melee damage: +5% melee crit",
    "Iron Will": "defensive: resist stuns and charms (no rank text)",
    "Unbridled Wrath": "rage: 60% chance of 1 extra Rage per hit",
    "Improved Cleave": "melee damage: Cleave deals more damage (no rank text)",
    "Piercing Howl": "grants_spell",
    "Blood Craze": "defensive: regenerate health after being crit",
    "Boundless Rage": "rage: more Rage (no rank text)",
    "Dual Wield Specialization": "melee damage: +25% off-hand damage and Rage",
    "Raging Blows": "rage: Cleave and Whirlwind cost 3 less Rage",
    "Enrage": "melee damage: +10% Physical damage after being hit",
    "Improved Execute": "rage: Execute costs 5 less Rage",
    "Precision": "melee damage: more melee hit (no rank text)",
    "Death Wish": "grants_spell",
    "Improved Intercept": "mobility: Intercept cooldown -10 s",
    "Improved Berserker Rage": "rage: Berserker Rage generates Rage (no rank text)",
    "Flurry": "melee damage: attack speed after a crit (no rank text)",
    "Bloodthirst": "grants_spell",
    # Protection
    "Shield Specialization": "defensive: +5% block, Rage on block",
    "Anticipation": "defensive: more defense or dodge (no rank text)",
    "Improved Bloodrage": "rage: Bloodrage generates more Rage (no rank text)",
    "Toughness": "defensive: more armor (no rank text)",
    "Improved Thunder Clap": "rage: Thunder Clap costs 6 less Rage",
    "Last Stand": "grants_spell",
    "Master of Defense": "rage: 5 Rage on dodge or parry with a shield",
    "Improved Revenge": "proc: Revenge can stun (no rank text)",
    "Defiance": "threat: +15% threat in Defensive Stance with a shield",
    "Improved Sunder Armor": "rage: Sunder Armor costs 3 less Rage",
    "Improved Disarm": "control: longer Disarm (no rank text)",
    "Vanguard": "defensive: shield and armor bonus (no rank text)",
    "Improved Shield Wall": "defensive: Shield Wall cooldown -11 min",
    "Concussion Blow": "grants_spell",
    "Improved Shield Bash": "control: Shield Bash also silences (no rank text)",
    "Bastion": "defensive: shield defense bonus (no rank text)",
    "Focused Rage": "rage: abilities cost less Rage (no rank text)",
    "Shield Slam": "grants_spell",
}

# Warrior skill lines in SkillLineAbility: Arms, Fury, Protection.
SKILL_LINES = (26, 256, 257)

# Shown on the dashboard while the class is routes-only (planning round 2, Q2/Q3).
SCORING_NOTE = "Arms and Fury scores come with the warrior damage model (#162); Protection stays unscored."
