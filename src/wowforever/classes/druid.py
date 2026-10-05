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

TALENT_EFFECTS: dict[str, tuple[EffectRule, ...]] = {}

# Every druid talent, with why it isn't modeled. TODO(#152): classify every talent.
UNMODELED: dict[str, str] = {}

# Druid skill lines in SkillLineAbility: Balance, Feral Combat, Restoration.
SKILL_LINES = (574, 134, 573)
