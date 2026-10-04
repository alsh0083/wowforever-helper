from dataclasses import replace

import pytest

from wowforever.schema import (
    ClassData, Dataset, Effect, Prerequisite, Provenance, SchemaError, SpellRank, Talent, Tree,
)

PROV = Provenance("wago.tools", "1.60.1.70205", "1.60.1.70205", "2026-10-04T00:00:00Z", "ab" * 32)


def make_dataset(**talent_overrides) -> Dataset:
    ignite = Talent(
        talent_id=34, name="Ignite", tree_id=1, row=2, col=0, max_rank=5,
        rank_spell_ids=(11119, 11120, 12846, 12847, 12848),
        rank_text=tuple(f"{8 * r}% of crit damage as fire over 4 sec" for r in range(1, 6)),
        effects=(Effect("dot_pct", (8, 16, 24, 32, 40), ("fire",)),),
        classic_status="changed",
    )
    impact = Talent(
        talent_id=35, name="Impact", tree_id=1, row=3, col=0, max_rank=5,
        rank_spell_ids=(), rank_text=(),
        prerequisite=Prerequisite(34, 5),
        effects=(Effect("proc_chance", (2, 4, 6, 8, 10)),),
    )
    impact = replace(impact, **talent_overrides)
    fire = Tree(1, "Fire", (34, 35))
    fireball = SpellRank(133, "Fireball", 1, 1, ("fire",), 1.5, mana_cost=30,
                         min_damage=14, max_damage=22, coefficient=0.123)
    mage = ClassData("mage", (fire,), (ignite, impact), (fireball,))
    return Dataset("1.60.1.70205", "1.60.1.70205", (mage,), (PROV,))


def test_valid_dataset_passes():
    make_dataset().validate()


def test_json_round_trip_is_lossless(tmp_path):
    ds = make_dataset()
    path = tmp_path / "ds.json"
    ds.save(path)
    assert Dataset.load(path) == ds


def test_lookup_helpers():
    mage = make_dataset().class_data("mage")
    assert mage.talent(35).name == "Impact"
    assert mage.talent_named("ignite").talent_id == 34


@pytest.mark.parametrize("override, message", [
    ({"prerequisite": Prerequisite(99, 1)}, "prerequisite 99 missing"),
    ({"prerequisite": Prerequisite(34, 6)}, "prerequisite rank 6 out of range"),
    ({"row": 1}, "must be earlier in the same tree"),
    ({"row": 2}, "shares position"),
    ({"effects": (Effect("magic", (1, 2, 3, 4, 5)),)}, "unknown effect kind"),
    ({"effects": (Effect("proc_chance", (1, 2)),)}, "has 2 values for max_rank 5"),
    ({"rank_text": ("only one",)}, "1 rank texts"),
    ({"classic_status": "maybe"}, "bad classic_status"),
    ({"tree_id": 7}, "unknown tree 7"),
])
def test_structural_problems_are_reported(override, message):
    with pytest.raises(SchemaError, match=message):
        make_dataset(**override).validate()


def test_missing_provenance_is_reported():
    with pytest.raises(SchemaError, match="no provenance"):
        replace(make_dataset(), provenance=()).validate()


def test_unsupported_schema_version_rejected():
    text = make_dataset().to_json().replace('"schema_version": 1', '"schema_version": 99')
    with pytest.raises(SchemaError, match="unsupported schema_version"):
        Dataset.from_json(text)
