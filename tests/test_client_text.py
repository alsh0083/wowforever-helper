"""Talent rank text from the client's own tooltip (#466), the fallback for a talent wowforevertalents.com links but
serves no page for. Call of Thunder (spell 16120, 70755 hotfixes): "Increases the critical strike chance of your
Lightning Bolt and Chain Lightning spells by $s1%." with effect 0 at 5."""

from wowforever.client_text import render, talent_texts

TEXT = "Increases the critical strike chance of your Lightning Bolt and Chain Lightning spells by $s1%."


def test_render_fills_effect_base_points():
    assert render(TEXT, {0: 5.0}) == ("Increases the critical strike chance of your Lightning Bolt and Chain Lightning "
                                      "spells by 5%.")
    assert render("Reduces the cost by $s2 and $s1%.", {0: -10.0, 1: 2.5}) == "Reduces the cost by 2.5 and 10%."


def test_render_refuses_tokens_it_cant_fill():
    assert render("Lasts $d.", {0: 5.0}) is None
    assert render(TEXT, {1: 5.0}) is None


def tables(*spells):
    return {"SpellName": [{"ID": str(i), "Name_lang": n} for i, n, _, _ in spells],
            "TraitDefinition": [{"SpellID": str(i)} for i, _, trait, _ in spells if trait],
            "Spell": [{"ID": str(i), "Description_lang": TEXT} for i, *_ in spells],
            "SpellEffect": [{"SpellID": str(i), "EffectIndex": "0", "EffectBasePointsF": str(p)}
                            for i, _, _, p in spells]}


def test_talent_texts_reads_the_talents_one_trait_spell():
    assert talent_texts(tables((16120, "Call of Thunder", True, 5)), "Call of Thunder") == (render(TEXT, {0: 5.0}),)
    # the same name on a non-talent spell doesn't count; two talent spells of one name are ambiguous
    assert talent_texts(tables((16120, "Call of Thunder", True, 5), (99, "Call of Thunder", False, 9)),
                        "Call of Thunder") == (render(TEXT, {0: 5.0}),)
    assert talent_texts(tables((1, "X", True, 5), (2, "X", True, 6)), "X") is None
    assert talent_texts(tables((1, "X", True, 5)), "Y") is None
