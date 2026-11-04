"""Tests reach a spec's build by its tree, not by build id: the 70755 re-import (#460) replaced every build id, and
the next import will again. Values pinned on these builds are consistency checks of the build the slot holds."""

from wowforever.builds import load_builds


def tree_build(cls, tree: str, variant: str | None = None, *, mode: str = "endgame"):
    """The class's build with the most points in `tree` (the PvP or PvE one when `variant` says; else PvP first),
    a community standard before a model build, ties by lowest id."""
    names = {t.name for t in cls.talents}

    def main_tree(build):
        if not set(build.final) <= names:
            return None
        ids = build.final_ids(cls)
        return max(cls.trees, key=lambda tr: (sum(ids.get(t, 0) for t in tr.talent_ids), -tr.tree_id)).name

    mine = [b for b in load_builds(class_name=cls.class_name) if b.mode == mode and main_tree(b) == tree
            and (variant is None or b.variant == variant)]
    if not mine:
        raise KeyError(f"{cls.class_name}: no {mode} {tree} build")
    return min(mine, key=lambda b: (b.variant != "PvP", b.origin != "community", b.id))


# Build ids tests used before the 70755 re-import (#460), each resolved to the build that holds its spec now.
OLD_IDS = {
    "mage": {"deep-arcane": ("Arcane", "PvE"), "deep-frost": ("Frost", "PvE"), "deep-fire": ("Fire", "PvE"),
             "arcane-pom-pyro": ("Arcane", "PvE")},
    "druid": {"druid-feral": ("Feral Combat", "PvE"), "druid-restoration": ("Restoration", "PvE"),
              "druid-balance": ("Balance", "PvE")},
    "shaman": {"shaman-elemental": ("Elemental", "PvE"), "shaman-enhancement-pve": ("Enhancement", "PvE")},
    "warlock": {"warlock-destruction-pve": ("Destruction", "PvE"), "warlock-demonology-pve-model": ("Demonology", "PvE")},
    "priest": {"priest-discipline-smite": ("Discipline", "PvE")},
    "warrior": {"warrior-arms": ("Arms", "PvP")},          # the Arms PvP build takes Mortal Strike; the PvE seed doesn't
}


def builds_by_id(class_name: str) -> dict:
    """Today's builds by id, plus the retired ids tests used (OLD_IDS), each mapped to its spec's build."""
    from wowforever.schema import Dataset, latest_dataset_path

    cls = Dataset.load(latest_dataset_path()).class_data(class_name)
    out = {b.id: b for b in load_builds(class_name=class_name)}
    for old, (tree, variant) in OLD_IDS.get(class_name, {}).items():
        out.setdefault(old, tree_build(cls, tree, variant))
    return out
