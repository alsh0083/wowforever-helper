"""The gearing line in build descriptions (#264): stat priority per point from the build's stat weights."""

from wowforever.describe import gearing

# rogue-assassination-pvp-model, level 30, from data/report-rogue.json (rounded)
ROGUE_30 = {"score": 0.0842, "strength": 0.000121, "agility": 0.000176, "stamina": 0.000606, "intellect": 0.0,
            "attack_power": 0.000121, "crit_rating": 0.000133, "hit_rating": 0.000137, "crit_pct": 0.000785,
            "hit_pct": 0.000814, "weapon_dps": 0.001147}
CASTER = {"score": 0.65, "spell_power": 0.0028, "hit_rating": 0.0042, "crit_rating": 0.0014, "intellect": 0.0007,
          "spirit": 0.0, "stamina": 0.0, "hit_pct": 0.0039, "crit_pct": 0.0034}


def test_levels_30_and_60_relative_to_the_best_stat():
    # 30: weapon DPS 1.147 is best; stamina .606/1.147 = 0.528 -> 0.53, agility .176/1.147 = 0.153 -> 0.15,
    #     hit rating .137/1.147 = 0.119 -> 0.12 (crit rating .133 -> 0.116 is fifth and dropped)
    # 60: hit rating .0042 is best; spell power .0028/.0042 = 0.667 -> 0.67, crit rating 0.333 -> 0.33,
    #     intellect 0.167 -> 0.17; spirit and stamina weigh 0 and are left out
    text = gearing({"20": CASTER, "30": ROGUE_30, "60": CASTER})
    assert text == ("Gear priority per point, relative to the best stat: at level 30, weapon DPS 1, stamina 0.53, "
                    "agility 0.15 and hit rating 0.12; at level 60, hit rating 1, spell power 0.67, crit rating 0.33 "
                    "and intellect 0.17. The Recommended gear panel ranks items by these weights at your level.")


def test_only_the_levels_present_are_described():
    assert gearing({"30": CASTER}).startswith(
        "Gear priority per point, relative to the best stat: at level 30, hit rating 1, spell power 0.67,")


def test_generic_weights_are_the_class_defaults():
    # 2.0 is best: intellect 1.0/2.0 = 0.5, stamina 0.5/2.0 = 0.25; ratios drop trailing zeros
    text = gearing({"generic": {"spell_power": 2.0, "intellect": 1.0, "stamina": 0.5}})
    assert text == ("Gear priority per point (the class's default weights; this build has no scores): "
                    "spell power 1, intellect 0.5 and stamina 0.25. The Recommended gear panel ranks items by "
                    "these weights at your level.")


def test_no_weights_no_line():
    assert gearing({}) == ""
    assert gearing({"40": CASTER}) == ""                      # neither 30 nor 60
    assert gearing({"30": {"score": 0.1, "hit_pct": 0.5}}) == ""   # no gear stats with weight
