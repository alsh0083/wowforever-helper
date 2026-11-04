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
