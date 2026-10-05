"""Hunter-specific knowledge: where the Forever hunter talent trees live in the client's trait data.

Stage 1 of the alts (#107): the trees and spells load, and every talent is classified. Ranged,
melee and pet damage are not modeled until the alts-engine milestone (#111). Pet abilities
(skill line 261) stay out of the spell list until then.
"""

from wowforever.classes import EffectRule, TraitLayout, TreeBand

# Trait tree 1091 holds all three hunter trees side by side, on the same grid as the mage's 1112.
LAYOUT = TraitLayout(
    class_name="hunter",
    trait_tree_id=1091,
    trees=(
        TreeBand(tree_id=1, name="Beast Mastery", min_x=1020),
        TreeBand(tree_id=2, name="Marksmanship", min_x=5020),
        TreeBand(tree_id=3, name="Survival", min_x=9080),
    ),
    first_row_y=2130,
    grid=600,
    # Classic nodes Forever parked off the grid (build 1.60.1.70205, #107): Lightning Reflexes
    # 104982 at (102800, 5740), replaced by node 110859 at Survival row 5, column 2; Improved
    # Serpent Sting 105003 at (6820, 39300), not on wowforevertalent.com (Improved Stings took over).
    hidden_nodes=frozenset({104982, 105003}),
)

TALENT_EFFECTS: dict[str, tuple[EffectRule, ...]] = {}

# Every hunter talent, with why it isn't modeled. Ranged, melee and pet damage wait for #111.
UNMODELED: dict[str, str] = {
    # Beast Mastery
    "Deadly Aspects": "proc: attack speed proc while Aspects of Hawk or Beast are active",
    "Endurance Training": "pet: +15% pet health and armor (#111)",
    "Focused Fire": "pet: +2% damage to you and your pet while it is active (#111)",
    "Improved Aspect of the Monkey": "defensive: bigger dodge from Aspect of the Monkey",
    "Pathfinding": "mobility: faster Aspect of the Cheetah and Aspect of the Pack",
    "Improved Revive Pet": "pet: faster, cheaper Revive Pet with more pet health (#111)",
    "Bestial Swiftness": "pet: +30% pet movement speed (#111)",
    "Unleashed Fury": "pet: +15% pet and hawk damage (#111)",
    "Improved Mend Pet": "pet: Mend Pet cleanse chance and lower mana cost (#111)",
    "Ferocity": "pet: +10% pet and hawk crit chance (#111)",
    "Summon Hawk": "grants_spell",
    "Spirit Bond": "pet: health regen for you and your pet while it is active (#111)",
    "Intimidation": "grants_spell",
    "Bestial Discipline": "resource: pet focus regen + 50% mana regen while casting",
    "Frenzy": "pet: pet attack speed proc after crits (#111)",
    "Bestial Wrath": "grants_spell",
    # Marksmanship
    "Hawk Eye": "utility: +6 yds ranged weapon range",
    "Improved Concussive Shot": "control: 20% chance to stun with Concussive Shot",
    "Lethal Attacks": "ranged damage: +5% crit chance with all attacks (#111)",
    "Improved Stings": "utility: Serpent Sting damage, Viper Sting cooldown and Sting durations",
    "Efficiency": "resource: -15% mana cost of Shots, Stings and melee",
    "Careful Aim": "ranged damage: attack power from intellect (#111)",
    "Rapid Killing": "ranged damage: Rapid Fire cooldown + shot damage after kills (#111)",
    "Improved Arcane Shot": "ranged damage: shorter Arcane Shot cooldown (#111)",
    "Lone Wolf": "pet: +20% damage with all attacks, solo play with no active pet (#111)",
    "Trueshot Aura": "grants_spell",
    "Mortal Shots": "ranged damage: +30% ranged crit damage (#111)",
    "Rapid Recuperation": "resource: mana regen while casting after Serpent Sting hits",
    "Barrage": "ranged damage: +10% Multi-Shot, Aimed Shot and Volley damage (#111)",
    "Scatter Shot": "grants_spell",
    "Ranged Weapon Specialization": "ranged damage: +5% ranged weapon damage (#111)",
    "Sniper Shot": "grants_spell",
    # Survival
    "Improved Tracking": "utility: +5% damage while tracking a creature type",
    "Deflection": "defensive: +5% parry chance",
    "Entrapment": "trap: triggered traps root affected targets",
    "Savage Strikes": "melee damage: +4% melee crit chance (#111)",
    "Survivalist": "defensive: +10% total health",
    "Improved Wing Clip": "control: 20% chance to immobilize with Wing Clip",
    "Clever Traps": "trap: longer freeze/frost and stronger immolation/explosive traps",
    "Surefooted": "mobility: +3% hit and -30% snare duration",
    "Deterrence": "grants_spell",
    "Survival Tactics": "trap: +10% hit with traps and Feign Death",
    "Predator's Edge": "melee damage: +30% melee crit damage, +50% off-hand damage (#111)",
    "Counterattack": "grants_spell",
    "Resourcefulness": "trap: -60% trap and melee mana cost, crit mana regen",
    "Expose Prey": "melee damage: chance to extend Mongoose Bite on marked prey (#111)",
    "Survivalist's Discipline": "trap: -40% trap and Deterrence cooldowns",
    "Strider Kick": "grants_spell",
    "Lightning Reflexes": "utility: +10% agility",
    "Lacerating Strikes": "melee damage: Mongoose Bite applies a bleed (#111)",
}

# Hunter skill lines in SkillLineAbility: Beast Mastery, Marksmanship, Survival.
SKILL_LINES = (50, 163, 51)
