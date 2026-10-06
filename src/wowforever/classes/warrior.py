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

# Every warrior talent, with why it isn't modeled. Talents marked "(no rank text)" are
# classified from the name: wowforevertalent.com is a build behind the client for them.
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
    "Iron Will": "defensive: resist stuns and charms (no rank text)",
    "Improved Cleave": "melee damage: Cleave deals more damage (no rank text)",
    "Piercing Howl": "grants_spell",
    "Blood Craze": "defensive: regenerate health after being crit",
    "Boundless Rage": "rage: more Rage (no rank text)",
    "Dual Wield Specialization": "melee damage: +25% off-hand damage and Rage",
    "Enrage": "melee damage: +10% Physical damage after being hit",
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

# Scored by the melee engine (#162): report_from_dataset builds a melee_report.
ENGINE = "melee"
# Tank tree: routes only, unscored (planning round 2, Q3).
UNSCORED_TREES = ("Protection",)

# Dashboard caveat for the warrior's scores (replaces the rogue/hunter one).
CAVEAT = ("Warrior model (#162): a two-hander's white swings build Rage for Mortal Strike, Whirlwind and "
          "Heroic Strike, against Classic combat-table rules. Fury dual wield, Bloodthirst, Flurry, Execute, "
          "Overpower and Slam aren't modeled yet, and base stats are estimates. Protection stays unscored. "
          "PvP uses the mage's duel model from the warrior's side.")

# Icons for talents wowforevertalent.com doesn't show (its page is a build behind, #149), by the client's
# SpellMisc.SpellIconFileDataID, named through wago.tools' documented file-info API (/api/info/{fdid}).
ICON_OVERRIDES = {
    "Improved Cleave": "ability_warrior_cleave",          # file 132338
    "Precision": "ability_marksmanship",                  # file 132222
    "Toughness": "spell_holy_devotion",                   # file 135892
    "Boundless Rage": "ability_warrior_intensifyrage",    # file 236310
}
