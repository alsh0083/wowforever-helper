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
