"""foreverlogs.gg summaries from browser HAR exports (#69): read only, names dropped."""

import json

from wowforever.sources.foreverlogs import import_hars, summarize_har


def entry(url, body):
    return {"request": {"url": url, "headers": []}, "response": {"headers": [], "content": {"text": json.dumps(body)}}}


def row(name, cls, spec, spell, dmg, hits, crits, kind="player"):
    return {"character_id": 1, "character_name": name, "character_class": cls, "character_type": kind,
            "character_spec": spec, "spell_id": 6603, "spell_name": spell, "total_damage": str(dmg),
            "casts": hits, "hits": hits, "crits": crits}


HAR = {"log": {"entries": [
    entry("https://foreverlogs.gg/api/reports/9", {"report": {"title": "RFK", "start_time": "2026-10-05T16:00:00Z"},
          "encounters": [{"id": 1, "name": "Boss A", "start_time": "2026-10-05T16:00:00Z",
                          "end_time": "2026-10-05T16:00:30Z", "success": True},
                         {"id": 2, "name": "Boss B", "start_time": "2026-10-05T16:05:00Z",
                          "end_time": "2026-10-05T16:05:30Z", "success": False}]}),
    entry("https://foreverlogs.gg/api/reports/9/character_spell_damage?encounterIds[]=1&encounterIds[]=2"
          "&format=by_source&participantType=friendlies",
          {"spell_damage_by_source": {
              "11": [row("Secretname", "Rogue", "Combat", "Auto Attack", 600, 40, 4),
                     row("Secretname", "Rogue", "Combat", "Sinister Strike", 300, 10, 1)],
              "12": [row("Wolfie", "Hunter", None, "Bite", 50, 5, 0, kind="pet")]}}),
    entry("https://foreverlogs.gg/api/icons/x.jpg", {}),
]}}


def test_summary_has_class_spec_shares_and_no_names():
    (s,) = summarize_har(HAR)
    assert (s["report"], s["seconds"], s["kills"], s["encounters"]) == (9, 60, 1, ["Boss A", "Boss B"])
    (p,) = s["players"]                                   # pets are left out
    assert (p["class"], p["spec"], p["damage"], p["dps"]) == ("Rogue", "Combat", 900, 15.0)
    assert [(a["spell"], a["share"], a["crit_pct"]) for a in p["abilities"]] == [
        ("Auto Attack", 0.667, 10.0), ("Sinister Strike", 0.333, 10.0)]
    assert "Secretname" not in json.dumps(s)


def test_import_merges_by_report_without_duplicates(tmp_path):
    har = tmp_path / "a.har"
    har.write_text(json.dumps(HAR), encoding="utf-8")
    out = tmp_path / "logs.json"
    import_hars([har], out)
    merged = import_hars([har, har], out)
    assert len(merged) == 1 and json.loads(out.read_text(encoding="utf-8")) == merged
