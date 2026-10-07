"""Group buffs, phase 1 (#218): resolved client values and the effective buff set of a party."""

from wowforever.group import Member, effective, load_resolved, options

BUFFS = load_resolved()["buffs"]
BY_ID = {b["id"]: b for b in BUFFS}


def at(buff_id, level):
    return (BY_ID[buff_id]["by_level"].get(str(level)) or {}).get("value")


def test_values_come_from_the_client_by_level():
    assert at("battle_shout", 60) == 139 and at("blessing_of_might", 60) == 133
    assert at("sunder_armor", 60) == 450 * 5            # five stacks on the boss
    assert at("windfury_totem", 31) is None and at("windfury_totem", 32) == 95
    assert at("leader_of_the_pack", 29) is None and at("leader_of_the_pack", 30) == 3   # Feral row 4
    assert at("curse_of_the_elements", 60) == 10
    assert any("lower than the rank" in n for n in BY_ID["hunters_mark"]["notes"])     # 98 at 40, 71 at 58


def test_options_give_one_choice_per_set_and_respect_role_and_tree():
    party = [Member("warrior", "Protection", "tank"), Member("paladin", "Holy", "healer"),
             Member("shaman", "Enhancement"), Member("druid", "Balance")]
    warrior, paladin, shaman, druid = options(BUFFS, party, 60)
    assert {o["id"] for opts in warrior for o in opts} == {"battle_shout", "sunder_armor"}
    blessing = next(opts for opts in paladin if any(o["id"] == "blessing_of_might" for o in opts))
    assert {o["id"] for o in blessing} == {"blessing_of_might", "blessing_of_kings"}       # one of them
    air = next(opts for opts in shaman if any(o["id"] == "windfury_totem" for o in opts))
    assert {o["id"] for o in air} == {"windfury_totem", "grace_of_air"}
    assert any(o["id"] == "moonkin_aura" for opts in druid for o in opts)
    assert not any(o["id"] == "leader_of_the_pack" for opts in druid for o in opts)       # Balance, not Feral
    dps_warrior = options(BUFFS, [Member("warrior", "Arms")], 60)[0]
    assert not any(o["id"] == "sunder_armor" for opts in dps_warrior for o in opts)       # only the tank sunders


def test_the_same_buff_from_two_providers_counts_once():
    picks = [{"id": "battle_shout", "stack": "battle_shout", "value": 139.0},
             {"id": "battle_shout", "stack": "battle_shout", "value": 111.0},
             {"id": "faerie_fire", "stack": "faerie_fire", "value": 505.0}]
    eff = effective(picks)
    assert set(eff) == {"battle_shout", "faerie_fire"} and eff["battle_shout"]["value"] == 139.0


def _engine(class_name, build_id):
    from pathlib import Path

    from wowforever import melee_scenarios as ms
    from wowforever.builds import load_builds
    from wowforever.classes import class_module
    from wowforever.effects import attach_effects
    from wowforever.schema import Dataset
    from wowforever.stats import StatTable

    m = class_module(class_name)
    cls, _ = attach_effects(Dataset.load(Path(__file__).parents[1] / "data" / "datasets" / "1.60.1.70205.json")
                            .class_data(class_name), m.TALENT_EFFECTS, m.UNMODELED)
    b = {x.id: x for x in load_builds(class_name=class_name)}[build_id]
    stats = StatTable.load("mage").at(60) if class_name == "mage" else ms.stat_table(class_name).at(60)
    return stats, cls, b.final_ids(cls)


def buff(buff_id, value, kind, reach, **more):
    return {buff_id: {"id": buff_id, "stack": buff_id, "value": value, "kind": kind, "reach": reach, **more}}


def test_buffs_reach_the_builds_they_should():
    from wowforever.group import dungeon_dps

    stats, cls, ranks = _engine("rogue", "rogue-combat")
    solo = dungeon_dps("rogue", stats, cls, ranks, {})
    assert dungeon_dps("rogue", stats, cls, ranks, buff("battle_shout", 139.0, "attack_power", "physical")) > solo
    assert dungeon_dps("rogue", stats, cls, ranks, buff("sunder_armor", 2250.0, "armor", "target")) > solo
    assert dungeon_dps("rogue", stats, cls, ranks, buff("windfury_totem", 246.0, "attack_power", "melee", proc_chance=0.2)) > solo
    assert dungeon_dps("rogue", stats, cls, ranks, buff("moonkin_aura", 3.0, "crit_pct", "casters")) == solo

    stats, cls, ranks = _engine("warlock", "warlock-affliction")
    solo = dungeon_dps("warlock", stats, cls, ranks, {})
    coe = dungeon_dps("warlock", stats, cls, ranks, buff("curse_of_the_elements", 10.0, "damage_taken_pct", "target"))
    assert abs(coe / solo - 1.10) < 1e-9                       # Curse of the Elements: +10% spell damage
    assert dungeon_dps("warlock", stats, cls, ranks, buff("battle_shout", 139.0, "attack_power", "physical")) == solo

    stats, cls, ranks = _engine("mage", "deep-frost")
    solo = dungeon_dps("mage", stats, cls, ranks, {})
    assert dungeon_dps("mage", stats, cls, ranks, buff("arcane_intellect", 31.0, "intellect", "casters")) > solo


def test_compositions_cover_every_group_once_with_probabilities_summing_to_one():
    from wowforever.group import compositions, load_weights

    comps = compositions(load_weights())
    assert abs(sum(p for p, _ in comps) - 1) < 1e-9
    assert all(party[0].role == "tank" and party[1].role == "healer" for _, party in comps)


def test_your_own_buffs_count_and_providers_pick_what_helps_you():
    from wowforever.group import Member, distribution

    # a warlock always has a curse of its own: the Elements for a caster
    dist = distribution(Member("warlock", "Affliction"), "caster", 60)
    assert all("curse_of_the_elements" in eff for _, eff in dist)
    # for a melee build, a shaman in the group drops Windfury rather than Grace of Air
    melee = distribution(Member("rogue", "Combat"), "melee", 60)
    with_shaman = [eff for _, eff in melee if "strength_of_earth" in eff]
    assert with_shaman and all("windfury_totem" in eff and "grace_of_air" not in eff for eff in with_shaman)


def test_the_probability_weighted_set_lands_near_the_full_expectation():
    from wowforever.group import grouped_dungeon, typical_dungeon_dps

    stats, cls, ranks = _engine("rogue", "rogue-combat")
    g = grouped_dungeon("rogue", stats, cls, ranks)
    assert g["low"] <= g["score"] <= g["high"] and g["unbuffed"] < g["score"]
    assert abs(typical_dungeon_dps("rogue", stats, cls, ranks) / g["score"] - 1) < 0.05
