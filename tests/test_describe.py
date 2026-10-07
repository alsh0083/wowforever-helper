"""Build descriptions (owner request, 2026-10-07): text from the model's data."""

from wowforever.describe import _join, playstyle, strengths


def test_join_reads_as_a_list():
    assert _join(["a"]) == "a" and _join(["a", "b"]) == "a and b" and _join(["a", "b", "c"]) == "a, b and c"


def test_caster_playstyle_names_dots_cooldowns_and_filler():
    text = playstyle("priest", {"kind": "caster", "dots": ["Shadow Word: Pain"], "cooldowns": ["Mind Blast"],
                                "filler": "Mind Flay"})
    assert text == ("In the model's rotation it keeps Shadow Word: Pain up, uses Mind Blast on cooldown and "
                    "fills with Mind Flay.")


def test_melee_playstyle_gives_the_damage_split():
    text = playstyle("rogue", {"kind": "rogue", "builder": "Sinister Strike",
                               "split": {"auto-attacks": 0.6, "abilities and poisons": 0.4}})
    assert "Sinister Strike" in text and "auto-attacks 60% and abilities and poisons 40%" in text


def test_strengths_name_the_best_and_worst_scenario_or_say_near_the_top():
    best = {"questing": 100.0, "raid": 200.0, "dungeon": 50.0}
    b = {"scores": {"questing": {"60": {"score": 90.0}}, "raid": {"60": {"score": 200.0}}, "dungeon": {"60": {"score": 30.0}}}}
    assert strengths(b, best) == ("Against the class's best build in each scenario at level 60 it is strongest at "
                                  "raid damage (100%) and questing speed (90%), and weakest at dungeon damage (60%).")
    top = {"scores": {"questing": {"60": {"score": 99.0}}, "raid": {"60": {"score": 199.0}}}}
    assert strengths(top, best) == "At level 60 it scores at or near the top of the class in raid damage and questing speed."
