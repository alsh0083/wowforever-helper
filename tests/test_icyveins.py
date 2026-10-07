"""Icy Veins guide builds (owner request, 2026-10-07): parsing and decoding, offline."""

from wowforever.sources.icyveins import decode, guide_class, guide_slugs, parse_guide

CALC = {"talentGroups": [
    {"name": "Discipline", "talents": [{"name": "Power in Light"}, {"name": "Wand Specialization"}, None]},
    {"name": "Shadow Magic", "talents": [None, {"name": "Spirit Tap"}, {"name": "Mind Flay"}]},
]}


def test_codes_index_the_talents_in_tree_order_skipping_empty_cells():
    # 0 Power in Light, 1 Wand Specialization, 2 Spirit Tap, 3 Mind Flay
    assert decode("1123", CALC) == ["Wand Specialization", "Wand Specialization", "Spirit Tap", "Mind Flay"]


def test_guides_are_found_on_the_hub_and_parsed_for_their_builds():
    hub = ('<a href="/wow-forever/shadow-priest-ranged-dps-pve-guide">x</a><a href="/wow-forever/deadmines-guide">y</a>'
           '<a href="/wow-forever/priest-class-overview">z</a>')
    assert guide_slugs(hub) == ["shadow-priest-ranged-dps-pve-guide"]
    assert guide_class("feral-druid-melee-dps-and-tank-pve-guide") == "druid"
    page = ('<p>Last Updated: Sep 17, 2026 - 8:00 PM</p><h2 id="level-30-talent-builds">Level 30 Talent Builds</h2>'
            '<h3 id="deep-shadow">Deep Shadow</h3><div data-talentcalculator-pointsurl="#tc-1123"></div>')
    assert parse_guide(page) == {"updated": "Sep 17, 2026",
                                 "builds": [{"code": "1123", "title": "Deep Shadow", "anchor": "deep-shadow", "level": 30}]}
