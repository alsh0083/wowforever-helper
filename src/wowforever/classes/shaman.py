"""Shaman-specific knowledge: where the Forever shaman talent trees live in the client's trait data.

Stage 1 of class-specific opponents (#34, #152): the trees and spells load and every talent is
classified; nothing is modeled yet. The shaman is an opponent, not a dashboard class.
"""

from wowforever.classes import EffectRule, TraitLayout, TreeBand

# Trait tree 1082 holds all three shaman trees side by side, on the same grid as the mage's 1112.
LAYOUT = TraitLayout(
    class_name="shaman",
    trait_tree_id=1082,
    trees=(
        TreeBand(tree_id=1, name="Elemental", min_x=1020),
        TreeBand(tree_id=2, name="Enhancement", min_x=5020),
        TreeBand(tree_id=3, name="Restoration", min_x=9080),
    ),
    first_row_y=2130,
    grid=600,
)

TALENT_EFFECTS: dict[str, tuple[EffectRule, ...]] = {}

# Every shaman talent, with why it isn't modeled. TODO(#152): classify every talent.
UNMODELED: dict[str, str] = {}

# Shaman skill lines in SkillLineAbility: Elemental, Enhancement, Restoration.
SKILL_LINES = (375, 373, 374)
