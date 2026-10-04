"""Mage-specific knowledge: where the Forever mage talent trees live in the client's trait data."""

from wowforever.classes import TraitLayout, TreeBand

# Forever builds its Classic-style trees on the modern Trait system (trait tree 1112 = all three
# mage trees side by side). The legacy Talent table in the client is stale and is not used.
LAYOUT = TraitLayout(
    class_name="mage",
    trait_tree_id=1112,
    trees=(
        TreeBand(tree_id=1, name="Arcane", min_x=1020),
        TreeBand(tree_id=2, name="Fire", min_x=5020),
        TreeBand(tree_id=3, name="Frost", min_x=9080),
    ),
    first_row_y=2130,
    grid=600,
)
