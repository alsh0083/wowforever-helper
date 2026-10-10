"""Warrior-specific knowledge: where the Forever warrior talent trees live in the client's trait data.

Stage 1 (#149, #155): trees, spells and every talent classified. Stage 2 (#162): Arms on the
melee engine; the damage talents carry effect rules from the rank text.
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

# Numbers are read from the rank text (#162); Anger Management and Death Wish are fixed effects
# in config/warrior.toml, taken or not.
TALENT_EFFECTS: dict[str, tuple[EffectRule, ...]] = {
    "Cruelty": (
        EffectRule("crit_chance", r"chance to get a critical strike with melee attacks by (\d+(?:\.\d+)?)%", ("all",)),
    ),
    "Two-Handed Weapon Specialization": (
        EffectRule("damage_pct", r"damage you deal with two-handed melee weapons by (\d+(?:\.\d+)?)%", ("@two_hand",)),
    ),
    "Impale": (
        EffectRule("crit_damage_pct", r"critical strike damage bonus of your abilities by (\d+(?:\.\d+)?)%", ("@ability",)),
    ),
    "Improved Overpower": (
        EffectRule("crit_chance", r"critical strike chance of your Overpower ability by (\d+(?:\.\d+)?)%", ("Overpower",)),
    ),
    "Improved Heroic Strike": (
        EffectRule("rage_cost", r"cost of your Heroic Strike ability by (\d+(?:\.\d+)?) Rage", ("Heroic Strike",), sign=-1),
    ),
    "Raging Blows": (
        EffectRule("rage_cost", r"Rage cost of your Cleave and Whirlwind abilities by (\d+(?:\.\d+)?)", ("Cleave", "Whirlwind"), sign=-1),
    ),
    "Improved Execute": (
        EffectRule("rage_cost", r"Rage cost of your Execute ability by (\d+(?:\.\d+)?)", ("Execute",), sign=-1),
    ),
    "Unbridled Wrath": (
        EffectRule("proc_chance", r"(\d+(?:\.\d+)?)% chance to generate 1 additional Rage", ("@white_rage",)),
    ),
    "Deep Wounds": (
        EffectRule("dot_pct", r"dealing (\d+(?:\.\d+)?)% of your melee weapon's average damage", ("@crit",)),
    ),
}

# Every warrior talent, with why it isn't modeled (trees as reworked in build 1.60.1.70291, #239).
UNMODELED: dict[str, str] = {
    # Arms
    "Deflection": "defensive: +5% parry",
    "Improved Rend": "melee damage: Rend bleeds 35% harder",
    "Improved Charge": "rage: Charge generates 6 more Rage",
    "Improved Tactical Mastery": "rage: keep 15 more Rage on stance change",
    "Anger Management": "rage: 1 Rage every 3 s in combat",
    "Spearing Strike": "grants_spell",
    "Bloodthrill": "proc: main-hand hits on Rend targets can enable an ability",
    "Sweeping Strikes": "grants_spell",
    "Weaponmaster": "melee damage: weapon-type bonus (crit, damage)",
    "Improved Slam": "melee damage: faster Slam that doesn't reset swings",
    "Improved Hamstring": "control: Hamstring has 15% chance to root 5 s",
    "Mortal Strike": "grants_spell",
    # Fury
    "Booming Voice": "shout: shouts reach 50% farther and cost 25% less",
    "Lingering Rage": "rage: Rage starts decaying up to 10 s later out of combat",
    "Piercing Howl": "grants_spell",
    "Blood Craze": "defensive: regenerate health after being crit",
    "Furious Precision": "melee damage: up to +10% off-hand hit (dual wield isn't modeled)",
    "Dual Wield Specialization": "melee damage: +25% off-hand damage and Rage",
    "Enrage": "melee damage: +10% Physical damage after being hit",
    "Death Wish": "grants_spell",
    "Improved Intercept": "mobility: Intercept cooldown -10 s",
    "Improved Berserker Rage": "rage: Berserker Rage generates 10 Rage and frees movement",
    "Flurry": "melee damage: +25% attack speed for 3 swings after a crit (not modeled yet)",
    "Gore Drinker": "defensive: rage abilities make the next 3 swings heal up to 1% Health",
    "Bloodthirst": "grants_spell",
    # Protection
    "Shield Specialization": "defensive: +5% block, Rage on block",
    "Improved Bloodrage": "rage: Bloodrage generates up to 50% more Rage",
    "Anticipation": "defensive: up to +20 Defense",
    "Iron Will": "defensive: stun and fear durations up to -15%",
    "Improved Thunder Clap": "rage: Thunder Clap costs 6 less Rage",
    "Last Stand": "grants_spell",
    "Master of Defense": "rage: 5 Rage on dodge or parry with a shield",
    "Improved Revenge": "melee damage: Revenge deals up to 60% more damage",
    "Defiance": "threat: +15% threat in Defensive Stance with a shield",
    "Improved Sunder Armor": "rage: Sunder Armor costs 3 less Rage",
    "Improved Disarm": "control: Disarm cooldown up to -20 s",
    "Vanguard": "mobility: Charge usable in Defensive Stance",
    "Improved Shield Wall": "defensive: Shield Wall cooldown -11 min",
    "Concussion Blow": "grants_spell",
    "Improved Shield Bash": "control: Shield Bash silences for 3 s",
    "Bastion": "melee damage: up to +10% damage with a shield (Protection is unscored)",
    "Focused Rage": "rage: offensive abilities cost up to 3 less Rage",
    "Shield Slam": "grants_spell",
}

# Warrior skill lines in SkillLineAbility: Arms, Fury, Protection.
SKILL_LINES = (26, 256, 257)

# Scored by the melee engine (#162): report_from_dataset builds a melee_report.
ENGINE = "melee"
# Tank tree: routes only, unscored (planning round 2, Q3).
UNSCORED_TREES = ("Protection",)

# Dashboard caveat for the warrior's scores (replaces the rogue/hunter one).
CAVEAT = ("Warrior model (#162): a two-hander's white swings build Rage for Mortal Strike, Whirlwind and "
          "Heroic Strike, against Classic combat-table rules. Fury dual wield, Bloodthirst, Flurry, Execute, "
          "Overpower and Slam aren't modeled yet, and base stats are estimates. Protection stays unscored. "
          "PvP uses the mage's duel model from the warrior's side.")

# Icons for talents wowforevertalent.com doesn't show, by the client's SpellMisc.SpellIconFileDataID, named
# through wago.tools' documented file-info API (/api/info/{fdid}). Empty since build 1.60.1.70291: the four
# it held (Improved Cleave, Precision, Toughness, Boundless Rage) left the trees (#239).
ICON_OVERRIDES: dict[str, str] = {}
