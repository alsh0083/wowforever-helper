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

# Numbers are read from the rank text (#175); Vengeance counts at full stacks.
TALENT_EFFECTS: dict[str, tuple[EffectRule, ...]] = {
    "Conviction": (
        EffectRule("crit_chance", r"critical strike with melee attacks by (\d+(?:\.\d+)?)%", ("all",)),
    ),
    "Two-Handed Weapon Specialization": (
        EffectRule("damage_pct", r"damage you deal with two-handed melee weapons by (\d+(?:\.\d+)?)%", ("@two_hand",)),
    ),
    "Vengeance": (
        EffectRule("damage_pct", r"Physical and Holy damage dealt by (\d+)% for \d+ sec after landing a non-periodic critical strike. Stacks up to (\d+) times",
                   ("all",), combine=lambda m: float(m.group(1)) * float(m.group(2))),
    ),
    "Sacred Arbiter": (
        EffectRule("damage_pct", r"damage of your Holy Strike ability by (\d+(?:\.\d+)?)%", ("Holy Strike",)),
    ),
    "Improved Judgement": (
        EffectRule("cooldown", r"cooldown of your Judgement ability by (\d+(?:\.\d+)?) sec", ("Judgement",), sign=-1),
    ),
    "Precision": (
        EffectRule("hit_chance", r"Improves your chance to hit by (\d+(?:\.\d+)?)%", ("all",)),
    ),
    "Improved Seals": (
        EffectRule("damage_pct", r"damage done by your Seals and Judgements by (\d+(?:\.\d+)?)%", ("Seal of Command", "Judgement")),
    ),
}

# Every paladin talent, with why it isn't modeled.
UNMODELED: dict[str, str] = {
    # Holy
    "Divine Strength": "buff: +10% Strength",
    "Divine Intellect": "buff: +10% Intellect",
    "Healing Light": "healing: +12% Holy Light, Flash of Light, Holy Shock",
    "Spiritual Focus": "utility: heals resist pushback",
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
    "Holy Conduit": "resource: cheaper Consecration, Holy Wrath, Exorcism, Hammer of Wrath",
    "Vindication": "proc: melee hits lower enemy attack power",
    "Sanctified Judgement": "resource: Judgement refunds seal mana",
    "Seal of Command": "grants_spell",
    "Pursuit of Justice": "mobility: +15% movement speed",
    "Eye for an Eye": "damage: reflects crit damage",
    "Repentance": "grants_spell",
    "Champion of the Light": "damage: spell damage from Intellect",
    "Instrument of Law": "damage: faster Hammer of Wrath, less threat",
    "Twist of Light": "resource: cheaper Seals, echo on seal swap",
}

# Paladin skill lines in SkillLineAbility: Holy, Protection, Retribution.
SKILL_LINES = (594, 267, 184)

# Retribution is scored by the melee engine (#175); healer and tank trees stay unscored (Q3).
ENGINE = "melee"
UNSCORED_TREES = ("Holy", "Protection")
CAVEAT = ("Retribution model (#175): a two-hander's white swings with Seal of Command procs, Judgement and Holy "
          "Strike on cooldown; Holy damage ignores armor. Seal of Command's proc rate and Judgement of Command's "
          "damage are Classic values. Consecration, Exorcism, Hammer of Wrath, Vindication, Divine Strength and "
          "mana aren't modeled; base stats are estimates. Holy and Protection stay unscored.")
