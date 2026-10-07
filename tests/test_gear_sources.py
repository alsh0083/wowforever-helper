"""Gear sources (#188): dungeon boss drops, quest rewards and crafted items, with faction.
Synthetic pages in the site's shapes; the real build runs on cached pages (data/items/gear.json)."""

import html
import json

from wowforever.gear_sources import (_site_item, build, crafted, item_classes, item_faction, parse_dungeon,
                                     parse_quests)


def astro(value):
    """Encode like the site's Astro props: every value tagged, lists [1, ...], everything else [0, ...]."""
    if isinstance(value, list):
        return [1, [astro(v) for v in value]]
    if isinstance(value, dict):
        return [0, {k: astro(v) for k, v in value.items()}]
    return [0, value]


def island(props):
    enc = {k: astro(v) for k, v in props.items()}
    return f'<astro-island props="{html.escape(json.dumps(enc))}"></astro-island>'


def test_quest_rows_give_faction_level_and_pickup():
    page = ('<article class="quest-row" id="quest-7" data-quest-card data-quest-id="7" data-faction="horde" '
            'data-location="ragefire-chasm" data-search="x"><button type="button" aria-label="Slay It #7. Accept 9. '
            'Quest 16. Horde. Pick up: Rahauro."></button></article>')
    assert parse_quests(page) == {7: {"name": "Slay It", "faction": "horde", "location": "ragefire-chasm",
                                      "accept": 9, "level": 16, "pickup": "Rahauro", "search": "x", "slug": None}}


def test_dungeon_rows_and_unconfirmed_classic_drops():
    page = ('<details class="dungeon-item dungeon-item-loot" id="item-872-brhahk-zor"><p>Dropped by Rhahk\'Zor.</p></details>'
            '<details class="dungeon-item dungeon-item-loot" id="item-5187-brhahk-zor"><p>Classic reference drop. '
            'Forever drop unconfirmed.</p></details>')
    assert parse_dungeon(page) == [(872, "rhahk-zor", True), (5187, "rhahk-zor", False)]


def test_faction_and_class_masks():
    assert item_faction({"AllowableRace_0": "-1"}) == "both"
    assert item_faction({"AllowableRace_0": str(1 | 4)}) == "alliance"          # Human, Dwarf
    assert item_faction({"AllowableRace_0": str(2 | 16)}) == "horde"            # Orc, Undead
    assert item_classes({"AllowableClass": "-1"}) is None
    assert item_classes({"AllowableClass": str(1 << 7)}) == ["mage"]


def test_site_records_map_stats_effects_slot_armor_and_weapon():
    item = _site_item({"name": "Rod", "itemLevel": 29, "requiredLevel": 24, "quality": 3, "slot": "Two-Hand",
                       "subclass": "Staves", "stats": [{"key": "int", "value": 11}, {"key": "firres", "value": 5}],
                       "effects": ["Equip: Increases damage and healing done by magical spells and effects by up to 7.",
                                   "Equip: Improves your chance to get a critical strike by 1%."],
                       "weapon": {"min": 53, "max": 80, "speed": 2.8, "dps": 23.8}})
    assert item["slot"] == "two_hand" and item["armor_type"] is None
    assert item["stats"] == {"intellect": 11, "spell_power": 7, "crit_pct": 1}
    assert item["weapon"] == {"min": 53, "max": 80, "speed": 2.8}
    assert _site_item({"name": "Gloves", "slot": "Hands", "subclass": "Leather Armor"})["armor_type"] == 2


def test_recipes_keep_the_real_skill():
    tables = {"SpellEffect": [{"SpellID": "10", "Effect": "24", "EffectItemType": "2307"},
                              {"SpellID": "11", "Effect": "24", "EffectItemType": "2307"}],
              "SkillLineAbility": [{"SkillLine": "165", "Spell": "10", "TrivialSkillLineRankLow": "95"},
                                   {"SkillLine": "165", "Spell": "11", "TrivialSkillLineRankLow": "40"},
                                   {"SkillLine": "999", "Spell": "10", "TrivialSkillLineRankLow": "1"}]}
    assert crafted(tables) == {2307: {"profession": "Leatherworking", "skill": 95}}


def test_build_keeps_boss_and_quest_sources_and_drops_rare_mobs():
    dungeons = island({"dungeons": [{"id": "dm", "name": "Deadmines", "levelMin": 17, "levelMax": 26}],
                       "lootById": {"dm": [{"observedBoss": "Sneed", "rosterKind": "boss", "items": []},
                                           {"observedBoss": "Miner Johnson", "rosterKind": "rare", "items": []}]}})
    detail = ('<details class="dungeon-item dungeon-item-loot" id="item-100-bsneed">Dropped by Sneed.</details>'
              '<details class="dungeon-item dungeon-item-loot" id="item-101-bminer-johnson">Dropped.</details>')
    items = island({"foreverRecords": [{"numericId": 200, "name": "Belt", "itemLevel": 20, "requiredLevel": None,
                                        "quality": 2, "slot": "Waist", "subclass": "Cloth Armor",
                                        "stats": [{"key": "sta", "value": 3}],
                                        "sources": [{"via": "choice", "questId": 7, "questName": "Slay It"}]}]})
    quests = ('<article class="quest-row" data-quest-id="7" data-faction="alliance" data-location="dm">'
              '<button aria-label="Slay It #7. Accept 15. Quest 20. Alliance. Pick up: Gryan."></button></article>')
    classic = [{"numericId": n, "name": f"Item {n}", "itemLevel": 22, "requiredLevel": 17, "quality": 2,
                "slot": "Hands", "stats": [{"key": "str", "value": 2}]} for n in (100, 101)]
    tables = {"ItemSparse": [], "RandPropPoints": [], "Item": [], "SpellEffect": [], "SkillLineAbility": []}
    out = build({"items": items, "dungeons": dungeons, "quests": quests, "dungeon-dm": detail,
                 "classic": json.dumps(classic)}, tables, checked_at="2026-10-06")
    by_id = {i["id"]: i for i in out["items"]}
    assert set(by_id) == {100, 200}                                   # the rare mob's drop is excluded
    assert by_id[100]["sources"] == [{"type": "boss", "dungeon": "dm", "boss": "Sneed", "confirmed": True, "level": 17}]
    quest = by_id[200]["sources"][0]
    assert quest["faction"] == "alliance" and quest["level"] == 20 and by_id[200]["required_level"] == 20


def test_quest_factions_resolve_in_order():
    from wowforever.gear_sources import resolve_factions

    quests = {1: {"faction": "unknown", "pickup": "Thom Filch", "search": ""},
              2: {"faction": "horde", "pickup": "Rahauro", "search": ""},
              3: {"faction": "unknown", "pickup": "Rahauro", "search": "stormwind"},
              4: {"faction": "unknown", "pickup": None, "search": "bring it to orgrimmar"},
              5: {"faction": "unknown", "pickup": None, "search": "ashenvale"},
              6: {"faction": "unknown", "pickup": None, "search": "stormwind or orgrimmar"},
              7: {"faction": "horde", "pickup": "Thom Filch", "search": ""}}
    rules = {"npcs": {"Thom Filch": {"faction": "alliance", "source": "owner"}},
             "places": {"alliance": ["stormwind"], "horde": ["orgrimmar"]}}
    resolve_factions(quests, rules)
    got = {q: (v["faction"], v["faction_basis"]) for q, v in quests.items()}
    assert got[1] == ("alliance", "owner")                              # owner's NPC override first
    assert got[7] == ("alliance", "owner")                              # ...even over a site record
    assert got[2] == ("horde", "recorded")
    assert got[3][0] == "horde" and got[3][1].startswith("likely: Rahauro")  # same NPC beats the text
    assert got[4] == ("horde", "likely: mentions orgrimmar")
    assert got[5] == ("unknown", None) and got[6] == ("unknown", None)  # contested or both: stays unrecorded


def test_quest_page_gives_objective_start_end_and_chain():
    from wowforever.gear_sources import parse_quest_page

    page = ('<h2>Objectives</h2><p>Kill Bazzalan, then return to Thrall.</p><ul></ul></section>'
            '<section><h2>Pick up</h2><p>Item start · Grimtotem Satchel · Player guide</p>'
            '<h2>Turn in</h2><p>Thrall · Orgrimmar · Named in the quest text</p>'
            '<p><strong>Prerequisite.</strong> Earlier step (id not in this listing).</p>'
            '<p><strong>Leads to.</strong> <a href="/quests/x-1/">Hidden Enemies</a></p>'
            '<p><strong>Recorded rewards.</strong> Not recorded</p>')
    assert parse_quest_page(page) == {
        "objective": "Kill Bazzalan, then return to Thrall.", "start": "Item: Grimtotem Satchel",
        "end": "Thrall · Orgrimmar",
        "chain": [["needs", "Earlier step (id not in this listing)."], ["next", "Hidden Enemies"]]}
    assert parse_quest_page("<h2>Pick up</h2><p>Not recorded</p>")["start"] is None


def test_crafted_items_wait_for_the_skill_they_need():
    from wowforever.gear_sources import skill_level

    assert [skill_level(s) for s in (None, 50, 75, 145, 225, 245, 300, 310)] == [1, 5, 5, 10, 20, 35, 35, 60]
