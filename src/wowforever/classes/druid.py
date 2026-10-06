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

# Numbers are read from the rank text (#163).
TALENT_EFFECTS: dict[str, tuple[EffectRule, ...]] = {
    "Improved Wrath": (
        EffectRule("cast_time", r"cast time of your Wrath spell by (\d+(?:\.\d+)?) sec", ("Wrath",), sign=-1),
        EffectRule("mana_cost_pct", r"its Mana cost by (\d+(?:\.\d+)?)%", ("Wrath",), sign=-1),
    ),
    "Genesis": (
        EffectRule("damage_pct", r"periodic damage and healing done by your spells and abilities by (\d+(?:\.\d+)?)%",
                   ("Moonfire", "Insect Swarm")),
    ),
    "Moonglow": (
        EffectRule("mana_cost_pct", r"Mana cost of your damaging spells by (\d+(?:\.\d+)?)%", ("arcane", "nature"), sign=-1),
    ),
    "Improved Moonfire": (
        EffectRule("damage_pct", r"damage and critical strike chance of your Moonfire spell by (\d+(?:\.\d+)?)%", ("Moonfire",)),
        EffectRule("crit_chance", r"damage and critical strike chance of your Moonfire spell by (\d+(?:\.\d+)?)%", ("Moonfire",)),
    ),
    "Nature's Majesty": (
        EffectRule("crit_chance", r"critical strike chance with spells and melee attacks by (\d+(?:\.\d+)?)%", ("all",)),
    ),
    "Nature's Reach": (
        EffectRule("hit_chance", r"improves your chance to hit by (\d+(?:\.\d+)?)%", ("arcane", "nature")),
    ),
    "Vengeance": (
        EffectRule("crit_damage_pct", r"critical strike damage bonus of your Arcane and Nature spells by (\d+(?:\.\d+)?)%",
                   ("arcane", "nature")),
    ),
    "Improved Starfire": (
        EffectRule("cast_time", r"cast time of Starfire by (\d+(?:\.\d+)?) sec", ("Starfire",), sign=-1),
    ),
    "Moonfury": (
        EffectRule("damage_pct", r"damage done by your Arcane and Nature spells by (\d+(?:\.\d+)?)%", ("arcane", "nature")),
    ),
    "Moonkin Form": (
        EffectRule("crit_chance", r"Critical Strike chance increased by (\d+(?:\.\d+)?)%", ("all",)),
    ),
    "Naturalist": (
        EffectRule("damage_pct", r"increases all damage you deal by (\d+(?:\.\d+)?)%", ("all",)),
    ),
    "Reflection": (
        EffectRule("regen_while_casting", r"Allows (\d+(?:\.\d+)?)% of your Mana regeneration", ("all",)),
    ),
}

# Every druid talent, with why it isn't modeled.
UNMODELED: dict[str, str] = {
    # Balance
    "Improved Entangling Roots": "control: stronger Entangling Roots",
    "Nature's Splendor": "damage: longer Moonfire, Rejuvenation, Regrowth, Insect Swarm",
    "Insect Swarm": "grants_spell",
    "Overgrowth": "control: Entangling Roots on 2 more targets",
    "Nature's Grace": "proc: spell crits speed up the next cast",
    "Eclipse": "proc: Wrath speeds up Starfire",
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
    "Subtlety": "threat: less threat from Nature and Arcane spells",
    "Natural Shapeshifter": "resource: cheaper shapeshifting",
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

# Scored by the caster spell engine (#163).
ENGINE = "spell"
ROTATION = {
    "dots": ("Moonfire", "Insect Swarm"),
    "cooldowns": (),
    "fillers": ("Starfire", "Wrath"),
}
# Feral (cat and bear) and Restoration wait for the melee hybrids and healing (#175, Q3).
UNSCORED_TREES = ("Feral Combat", "Restoration")
CAVEAT = ("Caster model (#163, #166): Moonfire and Insect Swarm kept up, then Starfire or Wrath. Eclipse, Nature's "
          "Grace and Omen of Clarity procs aren't modeled. Feral is unscored until the melee hybrids (#175); "
          "Restoration stays unscored. Base stats are estimates.")
