"""Rogue-specific knowledge: where the Forever rogue talent trees live in the client's trait data.

Stage 1 of the alts (#103): the trees and spells load, and every talent is classified. Melee
damage is not modeled until the alts-engine milestone (#111), so no talent has effect rules yet.
"""

from wowforever.classes import EffectRule, TraitLayout, TreeBand

# Trait tree 1111 holds all three rogue trees side by side, on the same grid as the mage's 1112.
LAYOUT = TraitLayout(
    class_name="rogue",
    trait_tree_id=1111,
    trees=(
        TreeBand(tree_id=1, name="Assassination", min_x=1020),
        TreeBand(tree_id=2, name="Combat", min_x=5020),
        TreeBand(tree_id=3, name="Subtlety", min_x=9080),
    ),
    first_row_y=2130,
    grid=600,
)

TALENT_EFFECTS: dict[str, tuple[EffectRule, ...]] = {}

# Every rogue talent, with why it isn't modeled. TODO (#103): fill from the rank text.
UNMODELED: dict[str, str] = {}

# Rogue skill lines in SkillLineAbility: Assassination, Combat, Subtlety, Poisons.
SKILL_LINES = (253, 38, 39, 40)
