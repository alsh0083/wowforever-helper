"""Where gear comes from (#188): dungeon boss drops, quest rewards and crafted items, with faction.

Sources:
- wowforevertalent.com (robots allows all): `/items/` (Forever item records with stats and sources),
  `/dungeons/` (loot per boss, with the kind of each drop), `/quests/` (quest faction, levels and
  pickup) and each reward quest's own page (objective, where it starts and ends, its chain). Pages are fetched only by `gear-sources --refresh`, 1.5 s apart, into data/cache/wft-gear/.
- The client item tables (cached, saved by hand per wago.tools' rules): stats, required level, slot,
  faction (allowed races) and class restrictions; recipes (profession spells that create items).

Blizzard makes the full item list hard to datamine, so the data is partial and grows as the site
records more; refresh on demand (planning 2026-10-06, Q7). Excluded (Q3/Q5): rare-mob drops, trash
drops and chests (often random bind-on-equip), and world drops. Vendor stock isn't recorded anywhere
reachable yet, so the alternative recommendation holds crafted items only.
"""

from __future__ import annotations

import html
import json
import re
import time
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from wowforever.gear import Item, load_items
from wowforever.normalize import Tables
from wowforever.sources.wowforevertalent import decode_astro

BASE = "https://wowforevertalent.com"
PAGES = ("items", "dungeons", "quests")
KEPT_DROPS = ("boss", "quest")                 # rosterKind values kept; rare, trash and object are not
PROFESSIONS = {164: "Blacksmithing", 165: "Leatherworking", 197: "Tailoring", 202: "Engineering"}
# The level each profession rank can be trained at (Classic): skill up to 75 / 150 / 225 / 300; above
# 300 is treated as level 60. Crafted items without a level requirement (most Engineering goggles) need
# the skill instead, so a recipe is no earlier than the level that can reach its skill.
SKILL_RANK_LEVELS = ((75, 5), (150, 10), (225, 20), (300, 35))


def skill_level(skill: int | None) -> int:
    """The earliest level that can train a profession to `skill`."""
    if not skill:
        return 1
    return next((level for cap, level in SKILL_RANK_LEVELS if skill <= cap), 60)
EFFECT_CREATE_ITEM = "24"
# Classic race ids: Human, Dwarf, Night Elf, Gnome / Orc, Undead, Tauren, Troll
ALLIANCE_RACES = (1 << 0) | (1 << 2) | (1 << 3) | (1 << 6)
HORDE_RACES = (1 << 1) | (1 << 4) | (1 << 5) | (1 << 7)
# Classic class ids for AllowableClass
CLASS_BITS = {"warrior": 1, "paladin": 2, "hunter": 3, "rogue": 4, "priest": 5, "shaman": 7, "mage": 8,
              "warlock": 9, "druid": 11}


def fetch_pages(cache_dir: Path, http_get: Callable[[str], str], *, delay: float = 1.5) -> None:
    """Save the three site pages, then each dungeon page with loot, into `cache_dir` (on demand only)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    for i, page in enumerate(PAGES):
        if i and delay:
            time.sleep(delay)
        (cache_dir / f"{page}.html").write_text(http_get(f"{BASE}/{page}/"), encoding="utf-8", newline="\n")
    time.sleep(delay)
    (cache_dir / "classic.json").write_text(http_get(f"{BASE}/items/classic.json"), encoding="utf-8", newline="\n")
    loot = _props((cache_dir / "dungeons.html").read_text(encoding="utf-8"))["lootById"]
    for dungeon_id, entries in loot.items():
        if entries:
            time.sleep(delay)
            (cache_dir / f"dungeon-{dungeon_id}.html").write_text(http_get(f"{BASE}/dungeons/{dungeon_id}/"),
                                                                   encoding="utf-8", newline="\n")
    # each reward quest's own page: where it starts and ends, and its chain
    quests = parse_quests((cache_dir / "quests.html").read_text(encoding="utf-8"))
    for qid in sorted(reward_quests(_props((cache_dir / "items.html").read_text(encoding="utf-8")))):
        if quests.get(qid, {}).get("slug"):
            time.sleep(delay)
            (cache_dir / f"quest-{qid}.html").write_text(http_get(f"{BASE}/quests/{quests[qid]['slug']}/"),
                                                        encoding="utf-8", newline="\n")


def reward_quests(items_page: Mapping[str, Any]) -> set[int]:
    """Ids of the quests that reward an item."""
    return {int(s["questId"]) for r in items_page["foreverRecords"] for s in r.get("sources") or []
            if s["via"] in ("choice", "fixed") and s.get("questId")}


def _props(page: str) -> dict[str, Any]:
    raw = re.search(r'<astro-island[^>]*props="([^"]*)"', page).group(1)
    return {k: decode_astro(v) for k, v in json.loads(html.unescape(raw)).items()}


def parse_quests(page: str) -> dict[int, dict[str, Any]]:
    """Quest id -> faction ("alliance", "horde" or "unknown"), location, levels and pickup."""
    out = {}
    for tag in re.findall(r'<article class="quest-row"[^>]*>.*?</article>', page, re.S):
        qid = re.search(r'data-quest-id="(\d+)"', tag)
        if not qid:
            continue
        label = html.unescape(re.search(r'aria-label="([^"]*)"', tag[tag.index("<button"):]).group(1))
        name = label.split(" #")[0]
        accept = re.search(r"Accept (\d+)", label)
        level = re.search(r"Quest (\d+)", label)
        pickup = re.search(r"Pick up: ([^.]+)\.", label)
        search = re.search(r'data-search="([^"]*)"', tag)
        slug = re.search(r'href="/quests/([^"/]+)/"', tag)
        out[int(qid.group(1))] = {
            "name": name, "faction": re.search(r'data-faction="([^"]*)"', tag).group(1),
            "location": re.search(r'data-location="([^"]*)"', tag).group(1),
            "accept": int(accept.group(1)) if accept else None, "level": int(level.group(1)) if level else None,
            "pickup": pickup.group(1).strip() if pickup else None,
            "search": html.unescape(search.group(1)) if search else "",
            "slug": slug.group(1) if slug else None,
        }
    return out


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", fragment))).strip()


def _place(text: str | None) -> str | None:
    """"Scout Riell · Sentinel Hill Tower · Named in the quest text" -> "Scout Riell · Sentinel Hill Tower";
    the site's notes on where it learned a place (player guide, quest text) are dropped."""
    if not text or text.lower().startswith("not recorded"):
        return None
    parts = [p for p in text.split(" · ") if p.lower() != "player guide" and not p.lower().startswith("named in")
             and not p.endswith(".")]
    if parts and parts[0] == "Item start":
        parts = [f"Item: {parts[1]}", *parts[2:]] if len(parts) > 1 else ["Starts from an item"]
    return " · ".join(parts) or None


def parse_quest_page(page: str) -> dict[str, Any]:
    """A quest page's objective, where it starts and ends, and the chain around it."""
    def after(heading: str) -> str | None:
        m = re.search(rf"<h2>{heading}</h2>\s*<p>(.*?)</p>", page, re.S)
        return _text(m.group(1)) if m else None

    chain = []
    for label, key in (("Prerequisite", "needs"), ("Comes after", "after"), ("Leads to", "next")):
        m = re.search(rf"<strong>{label}\.</strong>(.*?)</p>", page, re.S)
        if m and not _text(m.group(1)).lower().startswith("not recorded"):
            chain.append([key, _text(m.group(1))])
    return {"objective": after("Objectives"), "start": _place(after("Pick up")), "end": _place(after("Turn in")),
            "chain": chain}


def resolve_factions(quests: Mapping[int, dict[str, Any]], rules: Mapping[str, Any]) -> None:
    """Fill in factions the site hasn't recorded, with how each was decided (`faction_basis`):
    config/quest_factions.toml by quest, then by NPC; the site's record; the same pickup NPC's
    recorded quests; then faction cities and home zones named in the quest's text ("likely")."""
    by_quest, by_npc = rules.get("quests", {}), rules.get("npcs", {})
    places = rules.get("places", {})
    npc_faction: dict[str, set[str]] = {}
    for q in quests.values():
        if q["faction"] in ("alliance", "horde") and q.get("pickup"):
            npc_faction.setdefault(q["pickup"], set()).add(q["faction"])
    for qid, q in quests.items():
        q["faction_basis"] = "recorded" if q["faction"] in ("alliance", "horde") else None
        npc = q.get("pickup") or ""
        if str(qid) in by_quest:
            q["faction"], q["faction_basis"] = by_quest[str(qid)]["faction"], by_quest[str(qid)].get("source", "config")
        elif npc in by_npc:
            q["faction"], q["faction_basis"] = by_npc[npc]["faction"], by_npc[npc].get("source", "config")
        elif q["faction_basis"]:
            continue
        elif len(npc_faction.get(npc, ())) == 1:
            q["faction"], q["faction_basis"] = next(iter(npc_faction[npc])), f"likely: {npc} gives a recorded quest"
        else:
            text = q.get("search", "").lower()
            hits = {f: [p for p in words if p in text] for f, words in places.items()}
            sides = [f for f, found in hits.items() if found]
            if len(sides) == 1:
                q["faction"], q["faction_basis"] = sides[0], f"likely: mentions {', '.join(hits[sides[0]])}"


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def parse_dungeon(page: str) -> list[tuple[int, str, bool]]:
    """(item id, boss slug, confirmed in Forever) for each loot row of a dungeon page; Classic
    reference drops not yet seen in Forever are unconfirmed."""
    rows = re.finditer(r'<details class="dungeon-item dungeon-item-loot" id="item-(\d+)-b([^"]*)"(.*?)</details>',
                       page, re.S)
    return [(int(m.group(1)), m.group(2), "Forever drop unconfirmed" not in m.group(3)) for m in rows]


def item_faction(row: Mapping[str, str]) -> str:
    """"alliance", "horde" or "both" from ItemSparse's allowed races."""
    mask = int(row.get("AllowableRace_0", "-1") or -1)
    if mask in (-1, 0):
        return "both"
    alliance, horde = bool(mask & ALLIANCE_RACES), bool(mask & HORDE_RACES)
    return "both" if alliance == horde else "alliance" if alliance else "horde"


def item_classes(row: Mapping[str, str]) -> list[str] | None:
    """Classes allowed by ItemSparse's AllowableClass, or None when every class can use it."""
    mask = int(row.get("AllowableClass", "-1") or -1)
    if mask in (-1, 0):
        return None
    allowed = [c for c, bit in CLASS_BITS.items() if mask & (1 << (bit - 1))]
    return None if len(allowed) == len(CLASS_BITS) else allowed


def crafted(tables: Tables) -> dict[int, dict[str, Any]]:
    """Item id -> profession and skill for items a profession recipe creates."""
    creates = {row["SpellID"]: int(row["EffectItemType"]) for row in tables["SpellEffect"]
               if row["Effect"] == EFFECT_CREATE_ITEM and int(row["EffectItemType"] or 0) > 0}
    out = {}
    for row in tables["SkillLineAbility"]:
        line = int(row["SkillLine"])
        if line in PROFESSIONS and row["Spell"] in creates:
            item = creates[row["Spell"]]
            # the client keeps the skill where the recipe turns yellow, not the learn requirement;
            # duplicate rows exist, so keep the real recipe (the highest)
            skill = int(row["TrivialSkillLineRankLow"] or 0)
            if item not in out or skill > out[item]["skill"]:
                out[item] = {"profession": PROFESSIONS[line], "skill": skill}
    return out


SLOTS = {"head": "head", "neck": "neck", "shoulder": "shoulder", "back": "back", "chest": "chest",
         "wrist": "wrist", "hands": "hands", "waist": "waist", "legs": "legs", "feet": "feet",
         "finger": "finger", "trinket": "trinket", "main hand": "main_hand", "one-hand": "main_hand",
         "two-hand": "two_hand", "off hand": "off_hand", "held in off-hand": "off_hand", "shield": "off_hand",
         "ranged": "ranged", "thrown": "ranged", "relic": "ranged"}
ARMOR_TYPES = {"cloth": 1, "leather": 2, "mail": 3, "plate": 4}
# site stat keys -> the project's stat names (resistances, defense and healing-only bonuses are left out)
SITE_STATS = {"sta": "stamina", "int": "intellect", "spi": "spirit", "str": "strength", "agi": "agility",
              "spldmg": "spell_power", "mleatkpwr": "attack_power", "rgdatkpwr": "ranged_attack_power",
              "manargn": "mp5"}
# equip effects -> stat; crit and hit are percentages here, not ratings
EFFECTS = (
    (r"Increases damage and healing done by magical spells and effects by up to (\d+)", "spell_power"),
    (r"\+(\d+) Attack Power", "attack_power"),
    (r"Restores (\d+) mana per 5 sec", "mp5"),
    (r"chance to get a critical strike with spells by (\d+)%", "spell_crit_pct"),
    (r"chance to get a critical strike by (\d+)%", "crit_pct"),
    (r"chance to hit with spells by (\d+)%", "spell_hit_pct"),
    (r"chance to hit by (\d+)%", "hit_pct"),
)


def _site_item(record: Mapping[str, Any]) -> dict[str, Any]:
    """A wowforevertalent.com item record in the project's terms."""
    stats: dict[str, float] = {}
    for s in record.get("stats") or []:
        name = SITE_STATS.get(s["key"])
        if name and s.get("value"):
            stats[name] = stats.get(name, 0) + s["value"]
    for effect in record.get("effects") or []:
        text = effect if isinstance(effect, str) else effect.get("text", "")
        for pattern, name in EFFECTS:
            if m := re.search(pattern, text):
                stats[name] = stats.get(name, 0) + int(m.group(1))
                break
    parts = [p.strip().lower() for p in (record.get("slot") or "").split(",")]
    slot = next((SLOTS[k] for k in sorted(SLOTS, key=len, reverse=True) if parts and parts[0].startswith(k)), None)
    words = [w for p in parts[1:] + [(record.get("subclass") or "").lower()] for w in p.split()]
    armor = next((ARMOR_TYPES[w] for w in words if w in ARMOR_TYPES), None)
    weapon = record.get("weapon")
    return {"name": record["name"], "item_level": record.get("itemLevel"), "required_level": record.get("requiredLevel"),
            "quality": record.get("quality"), "slot": slot, "armor_type": armor, "stats": stats,
            "weapon": {k: weapon[k] for k in ("min", "max", "speed")} if weapon else None,
            "weapon_type": _weapon_type_from_name(" ".join(words + parts[:1]), slot)}


# Item.SubclassID for weapons (ClassID 2) -> type; two-handed variants share the one-handed name
WEAPON_SUBCLASSES = {0: "axe", 1: "axe", 2: "bow", 3: "gun", 4: "mace", 5: "mace", 6: "polearm", 7: "sword",
                     8: "sword", 10: "staff", 13: "fist", 15: "dagger", 16: "thrown", 18: "crossbow", 19: "wand"}
WEAPON_WORDS = (("staff", "staff"), ("staves", "staff"), ("polearm", "polearm"), ("crossbow", "crossbow"),
                ("bow", "bow"), ("gun", "gun"), ("thrown", "thrown"), ("wand", "wand"), ("dagger", "dagger"),
                ("fist", "fist"), ("axe", "axe"), ("mace", "mace"), ("sword", "sword"), ("shield", "shield"))


def _weapon_type_from_name(text: str, slot: str | None) -> str | None:
    """A weapon's type from the site's slot and subclass words; off hands without one are held items."""
    if slot not in ("main_hand", "two_hand", "off_hand", "ranged"):
        return None
    for word, kind in WEAPON_WORDS:
        if word in text:
            return kind
    return "held" if slot == "off_hand" else None


def _client_weapon_types(tables: Tables) -> dict[int, str]:
    """Weapon type from the client's Item table: weapon subclasses, shields, and held off-hand items."""
    out = {}
    for row in tables.get("Item", ()):
        cls, sub = int(row["ClassID"]), int(row["SubclassID"])
        if cls == 2 and sub in WEAPON_SUBCLASSES:
            out[int(row["ID"])] = WEAPON_SUBCLASSES[sub]
        elif cls == 4 and sub == 6:
            out[int(row["ID"])] = "shield"
        elif cls == 4 and sub == 0 and row.get("InventoryType") == "23":
            out[int(row["ID"])] = "held"
    return out


def _client_weapons(tables: Tables) -> dict[int, dict[str, float]]:
    """Weapon damage from the client's item-level damage tables, when they're cached."""
    if "ItemDamageOneHand" not in tables:
        return {}
    from wowforever.weapons import load_weapons

    return {w.item_id: {"min": w.min_damage, "max": w.max_damage, "speed": w.speed} for w in load_weapons(tables).values()}


def _faction_rules() -> dict[str, Any]:
    import tomllib

    path = Path(__file__).resolve().parents[2] / "config" / "quest_factions.toml"
    return tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def build(pages: Mapping[str, str], tables: Tables, *, checked_at: str,
          faction_rules: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The gear source dataset: every item with a kept source, its data and where it comes from."""
    items_page, dungeons_page = _props(pages["items"]), _props(pages["dungeons"])
    quests = parse_quests(pages["quests"])
    for qid, q in quests.items():
        if f"quest-{qid}" in pages:
            q.update(parse_quest_page(pages[f"quest-{qid}"]))
    resolve_factions(quests, faction_rules if faction_rules is not None else _faction_rules())
    dungeons = {d["id"]: {"name": d["name"], "level_min": d.get("levelMin"), "level_max": d.get("levelMax"),
                          "origin": d.get("origin")} for d in dungeons_page["dungeons"]}
    client: dict[int, Item] = {i.item_id: i for i in load_items(tables)}
    sparse = {int(r["ID"]): r for r in tables["ItemSparse"]}
    sources: dict[int, list[dict[str, Any]]] = {}
    site_items: dict[int, dict[str, Any]] = {}

    def add(item_id: int, source: dict[str, Any]) -> None:
        if source not in sources.setdefault(item_id, []):
            sources[item_id].append(source)

    for dungeon_id, entries in dungeons_page["lootById"].items():
        kinds = {_slug(e.get("observedBoss") or ""): (e.get("rosterKind"), e.get("observedBoss")) for e in entries}
        for entry in entries:
            if entry.get("rosterKind") not in KEPT_DROPS:
                continue
            for it in entry["items"]:
                add(int(it["numericId"]), {"type": "boss", "dungeon": dungeon_id, "boss": entry.get("observedBoss"),
                                           "confirmed": it.get("dropConfirmation") == "forever-observed"})
        for item_id, boss_slug, confirmed in parse_dungeon(pages.get(f"dungeon-{dungeon_id}", "")):
            kind, boss = kinds.get(boss_slug, (None, None))
            if kind in KEPT_DROPS:
                add(item_id, {"type": "boss", "dungeon": dungeon_id, "boss": boss, "confirmed": confirmed})
    for record in items_page["foreverRecords"]:
        item_id = int(record["numericId"])
        site_items[item_id] = _site_item(record)
        for src in record.get("sources") or []:
            if src["via"] == "drop" and src.get("dungeonId"):
                add(item_id, {"type": "boss", "dungeon": src["dungeonId"], "boss": src.get("boss"), "confirmed": True})
            elif src["via"] in ("choice", "fixed") and src.get("questId"):
                q = quests.get(int(src["questId"]), {})
                add(item_id, {"type": "quest", "quest": src.get("questName") or q.get("name"),
                              "quest_id": int(src["questId"]), "faction": q.get("faction", "unknown"), "faction_basis": q.get("faction_basis"),
                              "pickup": q.get("pickup"), "dungeon": q.get("location"),
                              "level": q.get("level") or q.get("accept"), "objective": q.get("objective"),
                              "start": q.get("start"), "end": q.get("end"), "chain": q.get("chain") or []})
    for item_id, recipe in crafted(tables).items():
        add(item_id, {"type": "crafted", **recipe})

    # Blizzard withholds most dungeon items from the client tables; the site's Classic catalog has them
    classic = {int(r["numericId"]): _site_item(r) for r in json.loads(pages.get("classic", "[]"))}
    weapons = _client_weapons(tables)
    weapon_types = _client_weapon_types(tables)
    out = []
    for item_id, srcs in sorted(sources.items()):
        if item_id in client:
            c = client[item_id]
            data = {"name": c.name, "item_level": c.item_level, "required_level": c.required_level,
                    "quality": c.quality, "slot": c.slot, "armor_type": c.armor_type, "stats": c.stats,
                    "weapon": weapons.get(item_id),
                    "weapon_type": weapon_types.get(item_id), "data": "client"}
        elif item_id in site_items:
            data = {**site_items[item_id], "data": "site"}
        elif item_id in classic:
            data = {**classic[item_id], "data": "site-classic"}
        else:
            continue                          # no stats from any source yet
        if not data["slot"]:
            continue                          # not gear we can place (bags, quest items)
        # the level each source becomes available at: a dungeon's lower bound, a quest's level, else
        # the item's own requirement; items without a recorded requirement use their earliest source
        for s in srcs:
            if s["type"] == "boss":
                s["level"] = (dungeons.get(s["dungeon"]) or {}).get("level_min")
            elif s["type"] == "crafted":
                s["level"] = max(data["required_level"] or 1, skill_level(s.get("skill")))
        if data["required_level"] is None:
            levels = [s["level"] for s in srcs if s.get("level")]
            if not levels:
                continue
            data["required_level"] = min(levels)
        row = sparse.get(item_id, {})
        out.append({"id": item_id, **data, "faction": item_faction(row), "classes": item_classes(row),
                    "sources": srcs})
    return {"checked_at": checked_at, "source": "wowforevertalent.com + client item tables",
            "dungeons": dungeons, "items": out}


def write(dataset: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dataset, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")


def now() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def load_pages(cache_dir: Path) -> dict[str, str]:
    pages = {p: (cache_dir / f"{p}.html").read_text(encoding="utf-8") for p in PAGES}
    if (cache_dir / "classic.json").exists():
        pages["classic"] = (cache_dir / "classic.json").read_text(encoding="utf-8")
    for path in [*cache_dir.glob("dungeon-*.html"), *cache_dir.glob("quest-*.html")]:
        pages[path.stem] = path.read_text(encoding="utf-8")
    return pages


def summary(dataset: Mapping[str, Any]) -> str:
    from collections import Counter

    kinds = Counter(s["type"] for i in dataset["items"] for s in i["sources"])
    return (f"{len(dataset['items'])} items ({', '.join(f'{n} {k}' for k, n in sorted(kinds.items()))}); "
            f"checked {dataset['checked_at']}")
