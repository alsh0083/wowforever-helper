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

# Every paladin talent, with why it isn't modeled. TODO(#152): classify every talent.
UNMODELED: dict[str, str] = {}

# Paladin skill lines in SkillLineAbility: Holy, Protection, Retribution.
SKILL_LINES = (594, 267, 184)
