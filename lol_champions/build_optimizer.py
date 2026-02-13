"""Build optimizer for finding the best item combinations.

Given a champion, target, combo duration, and number of item slots,
searches over valid item combinations to find the build that maximizes
DPS.  Uses exhaustive search (all combos) for ≤3 items, and greedy
iterative search for 4-6 items.

All item stats are hardcoded in ITEM_CATALOG.  Use ``validate_catalog()``
with a DataDragon instance to detect patch-drift on the stats DDragon
can verify (AD, HP, AS, armor, MR, AP).
"""

import itertools
import sys
from collections import defaultdict
from typing import Any, Dict, List

from .dps import optimize_dps
from .items import (
    SpearOfShojin,
    BladeOfTheRuinedKing, WitsEnd, NashorsTooth, RecurveBow, Terminus,
    TitanicHydra,
    KrakenSlayer,
    TrinityForce, IcebornGauntlet, LichBane,
    VoltaicCyclosword, RapidFirecannon, StatikkShiv, Stormrazor,
    LordDominiksRegards,
    Stridebreaker, ProfaneHydra, RavenousHydra,
    HextechRocketbelt, Everfrost, HextechGunblade,
    LiandrysTorment, SunfireAegis, HollowRadiance,
    SunderedSky, DeadMansPlate,
    Tiamat, GuinsoosRageblade,
)


# ═══════════════════════════════════════════════════════════════════════
# ITEM CATALOG
# ═══════════════════════════════════════════════════════════════════════
#
# Each entry: {
#   "id":        Riot item ID,
#   "stats":     dict compatible with champion.add_stats(**stats),
#   "proc":      dataclass *class* (not instance) or None,
#   "exclusive": list of group names (max 1 per group in a build),
# }
#
# Stats sourced from https://leagueoflegends.fandom.com/wiki/ (patch 16.3)
# Only stats that affect combat damage are included.

ITEM_CATALOG: Dict[str, Dict[str, Any]] = {
    # ─── Stacking amplifier ───
    "Spear of Shojin": {
        "id": 3161,
        "stats": {"bonus_AD": 45, "bonus_HP": 450},
        "proc": SpearOfShojin,
        "exclusive": [],
    },

    # ─── On-hit items ───
    "Blade of the Ruined King": {
        "id": 3153,
        "stats": {"bonus_AD": 40, "bonus_AS": 25, "life_steal": 0.08},
        "proc": BladeOfTheRuinedKing,
        "exclusive": [],
    },
    "Wit's End": {
        "id": 3091,
        "stats": {"bonus_AD": 40, "bonus_AS": 40, "bonus_MR": 40},
        "proc": WitsEnd,
        "exclusive": [],
    },
    "Nashor's Tooth": {
        "id": 3115,
        "stats": {"bonus_AP": 100, "bonus_AS": 50},
        "proc": NashorsTooth,
        "exclusive": [],
    },
    "Recurve Bow": {
        "id": 1043,
        "stats": {"bonus_AS": 15},
        "proc": RecurveBow,
        "exclusive": [],
    },
    "Terminus": {
        "id": 3302,
        "stats": {"bonus_AD": 30, "bonus_AS": 30},
        "proc": Terminus,
        "exclusive": [],
    },
    "Titanic Hydra": {
        "id": 3748,
        "stats": {"bonus_AD": 50, "bonus_HP": 500},
        "proc": TitanicHydra,
        "exclusive": ["hydra"],
    },

    # ─── Stacking on-hit ───
    "Kraken Slayer": {
        "id": 6672,
        "stats": {"bonus_AD": 40, "bonus_AS": 25},
        "proc": KrakenSlayer,
        "exclusive": [],
    },

    # ─── Spellblade ───
    "Trinity Force": {
        "id": 3078,
        "stats": {"bonus_AD": 35, "bonus_HP": 300, "bonus_AS": 33},
        "proc": TrinityForce,
        "exclusive": ["spellblade"],
    },
    "Iceborn Gauntlet": {
        "id": 6662,
        "stats": {"bonus_HP": 300, "bonus_AR": 50},
        "proc": IcebornGauntlet,
        "exclusive": ["spellblade"],
    },
    "Lich Bane": {
        "id": 3100,
        "stats": {"bonus_AP": 85},
        "proc": LichBane,
        "exclusive": ["spellblade"],
    },

    # ─── Energized ───
    "Voltaic Cyclosword": {
        "id": 2015,
        "stats": {"bonus_AD": 55, "bonus_AS": 15},
        "proc": VoltaicCyclosword,
        "exclusive": [],
    },
    "Rapid Firecannon": {
        "id": 3094,
        "stats": {"bonus_AS": 25},
        "proc": RapidFirecannon,
        "exclusive": [],
    },
    "Statikk Shiv": {
        "id": 3087,
        "stats": {"bonus_AS": 45},
        "proc": StatikkShiv,
        "exclusive": [],
    },
    "Stormrazor": {
        "id": 3095,
        "stats": {"bonus_AD": 45},
        "proc": Stormrazor,
        "exclusive": [],
    },

    # ─── Damage amplifier ───
    "Lord Dominik's Regards": {
        "id": 3036,
        "stats": {"bonus_AD": 35, "armor_pen_pct": 0.30},
        "proc": LordDominiksRegards,
        "exclusive": [],
    },

    # ─── Active items ───
    "Stridebreaker": {
        "id": 6631,
        "stats": {"bonus_AD": 45, "bonus_HP": 300, "bonus_AS": 20},
        "proc": Stridebreaker,
        "exclusive": [],
    },
    "Profane Hydra": {
        "id": 6698,
        "stats": {"bonus_AD": 60, "lethality": 18},
        "proc": ProfaneHydra,
        "exclusive": ["hydra"],
    },
    "Ravenous Hydra": {
        "id": 3074,
        "stats": {"bonus_AD": 65, "life_steal": 0.10},
        "proc": RavenousHydra,
        "exclusive": ["hydra"],
    },
    "Hextech Rocketbelt": {
        "id": 3152,
        "stats": {"bonus_AP": 80, "bonus_HP": 300},
        "proc": HextechRocketbelt,
        "exclusive": [],
    },
    "Everfrost": {
        "id": 6656,
        "stats": {"bonus_AP": 70, "bonus_HP": 300},
        "proc": Everfrost,
        "exclusive": [],
    },
    "Hextech Gunblade": {
        "id": 3146,
        "stats": {"bonus_AD": 40, "bonus_AP": 60},
        "proc": HextechGunblade,
        "exclusive": [],
    },

    # ─── Burn / Immolate ───
    "Liandry's Torment": {
        "id": 3068,
        "stats": {"bonus_AP": 80, "bonus_HP": 300},
        "proc": LiandrysTorment,
        "exclusive": [],
    },
    "Sunfire Aegis": {
        "id": 3001,
        "stats": {"bonus_AR": 50, "bonus_HP": 500},
        "proc": SunfireAegis,
        "exclusive": ["immolate"],
    },
    "Hollow Radiance": {
        "id": 4401,
        "stats": {"bonus_MR": 50, "bonus_HP": 500},
        "proc": HollowRadiance,
        "exclusive": ["immolate"],
    },

    # ─── Conditional ───
    "Sundered Sky": {
        "id": 6694,
        "stats": {"bonus_AD": 50, "bonus_HP": 300},
        "proc": SunderedSky,
        "exclusive": [],
    },
    "Dead Man's Plate": {
        "id": 3742,
        "stats": {"bonus_HP": 300, "bonus_AR": 45},
        "proc": DeadMansPlate,
        "exclusive": [],
    },

    # ─── Misc ───
    "Tiamat": {
        "id": 3077,
        "stats": {"bonus_AD": 25},
        "proc": None,
        "exclusive": ["hydra"],
    },
    "Guinsoo's Rageblade": {
        "id": 3124,
        "stats": {"bonus_AS": 30},
        "proc": GuinsoosRageblade,
        "exclusive": [],
    },

    # ─── Stat-only items (no proc dataclass) ───
    "Death's Dance": {
        "id": 6333,
        "stats": {"bonus_AD": 55, "bonus_HP": 300},
        "proc": None,
        "exclusive": [],
    },
    "Sterak's Gage": {
        "id": 3053,
        "stats": {"bonus_AD": 50, "bonus_HP": 400},
        "proc": None,
        "exclusive": [],
    },
    "Maw of Malmortius": {
        "id": 3156,
        "stats": {"bonus_AD": 55, "bonus_MR": 50},
        "proc": None,
        "exclusive": [],
    },
    "Guardian Angel": {
        "id": 3026,
        "stats": {"bonus_AD": 40, "bonus_AR": 40},
        "proc": None,
        "exclusive": [],
    },
    "Experimental Hexplate": {
        "id": 1502,
        "stats": {"bonus_AD": 55, "bonus_HP": 300},
        "proc": None,
        "exclusive": [],
    },
}


# ═══════════════════════════════════════════════════════════════════════
# DATA DRAGON VALIDATION
# ═══════════════════════════════════════════════════════════════════════

# Mapping from our stat keys to DataDragon stat keys
_STAT_MAP = {
    "bonus_AD": "ad",
    "bonus_AP": "ap",
    "bonus_HP": "hp",
    "bonus_AR": "armor",
    "bonus_MR": "mr",
    "bonus_AS": "attack_speed_pct",
}


def validate_catalog(dd) -> list[str]:
    """Compare ITEM_CATALOG stats against DataDragon.

    Only checks stats that DataDragon reliably provides:
    AD, AP, HP, armor, MR, attack speed %.

    Args:
        dd: A DataDragon instance.

    Returns:
        List of warning strings for mismatches. Empty if all match.
    """
    warnings = []
    for name, entry in ITEM_CATALOG.items():
        dd_stats = dd.item_stats(entry["id"])
        for our_key, dd_key in _STAT_MAP.items():
            our_val = entry["stats"].get(our_key, 0)
            dd_val = dd_stats.get(dd_key, 0)
            if abs(our_val - dd_val) > 0.5:
                warnings.append(
                    f"{name}: {our_key} = {our_val} (catalog) vs "
                    f"{dd_val} (DataDragon)"
                )
    return warnings


# ═══════════════════════════════════════════════════════════════════════
# BUILD HELPERS
# ═══════════════════════════════════════════════════════════════════════


def _is_valid_combo(item_names: tuple) -> bool:
    """Check that a combo respects exclusive-group constraints."""
    groups: Dict[str, int] = defaultdict(int)
    for name in item_names:
        for g in ITEM_CATALOG[name].get("exclusive", []):
            groups[g] += 1
            if groups[g] > 1:
                return False
    return True


def _apply_build(champion, item_names) -> tuple:
    """Apply item stats to champion and return (combined_stats, proc_instances)."""
    combined: Dict[str, float] = {}
    procs: list = []
    for name in item_names:
        entry = ITEM_CATALOG[name]
        for stat, val in entry["stats"].items():
            combined[stat] = combined.get(stat, 0) + val
        if entry.get("proc"):
            procs.append(entry["proc"]())
    champion.add_stats(**combined)
    return combined, procs


def _undo_build(champion, stats_applied: dict):
    """Remove previously applied item stats from champion."""
    negated = {k: -v for k, v in stats_applied.items()}
    champion.add_stats(**negated)


def _resolve_pool(pool=None, exclude=None) -> list:
    """Determine which items are in the search pool."""
    if pool is not None:
        names = [n for n in pool if n in ITEM_CATALOG]
    else:
        names = list(ITEM_CATALOG.keys())
    if exclude:
        ex_set = set(exclude)
        names = [n for n in names if n not in ex_set]
    return names


# ═══════════════════════════════════════════════════════════════════════
# SEARCH STRATEGIES
# ═══════════════════════════════════════════════════════════════════════


def _evaluate_build(champion, target, item_names, time_limit,
                    rune, damage_modifiers, r_active) -> dict:
    """Score a single build: apply stats, run optimizer, undo, return result."""
    stats, procs = _apply_build(champion, item_names)
    try:
        result = optimize_dps(
            champion=champion,
            target=target,
            time_limit=time_limit,
            rune=rune,
            damage_modifiers=damage_modifiers,
            items=procs if procs else None,
            r_active=r_active,
        )
    finally:
        _undo_build(champion, stats)
    return {
        "items": list(item_names),
        "total_damage": result["total_damage"],
        "dps": result["dps"],
        "total_healing": result["total_healing"],
        "sequence": result["sequence"],
        "timeline": result["timeline"],
        "stats_applied": stats,
    }


def _exhaustive_search(champion, target, pool, item_count, time_limit,
                       rune, damage_modifiers, r_active, top_n,
                       progress=True) -> list:
    """Try every valid combination and return top N by DPS."""
    results = []
    total = 0
    valid = 0

    # Count total combos for progress reporting
    all_combos = list(itertools.combinations(pool, item_count))
    total_combos = len(all_combos)

    best_dps = 0.0
    best_items = []

    for i, combo in enumerate(all_combos):
        total += 1
        if not _is_valid_combo(combo):
            continue
        valid += 1

        result = _evaluate_build(
            champion, target, combo, time_limit,
            rune, damage_modifiers, r_active,
        )
        results.append(result)

        if result["dps"] > best_dps:
            best_dps = result["dps"]
            best_items = result["items"]

        if progress and valid % 50 == 0:
            names = " + ".join(best_items)
            print(f"  [{valid}/{total_combos}] Best: {names} = {best_dps} DPS",
                  file=sys.stderr, flush=True)

    results.sort(key=lambda r: r["dps"], reverse=True)
    return results[:top_n]


def _greedy_search(champion, target, pool, item_count, time_limit,
                   rune, damage_modifiers, r_active, top_n,
                   progress=True) -> list:
    """Greedy iterative: pick the best item for each slot sequentially."""
    chosen: list = []
    remaining = list(pool)

    for slot in range(item_count):
        best_result = None
        best_name = None

        for name in remaining:
            candidate = chosen + [name]
            if not _is_valid_combo(tuple(candidate)):
                continue

            result = _evaluate_build(
                champion, target, tuple(candidate), time_limit,
                rune, damage_modifiers, r_active,
            )

            if best_result is None or result["dps"] > best_result["dps"]:
                best_result = result
                best_name = name

        if best_name is None:
            break

        chosen.append(best_name)
        remaining.remove(best_name)

        if progress:
            names = " + ".join(chosen)
            print(f"  Slot {slot + 1}/{item_count}: {names} = "
                  f"{best_result['dps']} DPS", file=sys.stderr, flush=True)

    # Final evaluation with the complete build
    if not chosen:
        return []

    final = _evaluate_build(
        champion, target, tuple(chosen), time_limit,
        rune, damage_modifiers, r_active,
    )
    return [final]


# ═══════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════


def optimize_build(
    champion,
    target,
    time_limit: float,
    item_count: int,
    rune=None,
    damage_modifiers=None,
    pool: list = None,
    exclude: list = None,
    strategy: str = "auto",
    top_n: int = 5,
    r_active: bool = False,
    progress: bool = True,
) -> List[Dict[str, Any]]:
    """Find the best item build by DPS.

    Searches over valid item combinations from the pool, applies their
    stats and proc effects to the champion, runs ``optimize_dps()`` for
    each, and returns the top builds sorted by DPS.

    Args:
        champion: Champion instance at the desired level.
        target: Target with armor, MR, HP.
        time_limit: Combo duration in seconds (e.g. 5.0).
        item_count: Number of item slots to fill (1-6).
        rune: Optional keystone rune instance.
        damage_modifiers: Static amp modifiers list.
        pool: Whitelist of item names. None = all items.
        exclude: Blacklist of item names to skip.
        strategy: ``"exhaustive"`` | ``"greedy"`` | ``"auto"``.
            Auto uses exhaustive for ≤3 items, greedy for >3.
        top_n: Number of top builds to return.
        r_active: If True, R is pre-activated.
        progress: Print progress to stderr.

    Returns:
        List of dicts sorted by DPS (descending), each with:
        ``items``, ``total_damage``, ``dps``, ``total_healing``,
        ``sequence``, ``stats_applied``.
    """
    resolved = _resolve_pool(pool, exclude)
    if len(resolved) < item_count:
        raise ValueError(
            f"Pool has {len(resolved)} items but item_count is {item_count}"
        )

    if strategy == "auto":
        use_exhaustive = item_count <= 3
    elif strategy == "exhaustive":
        use_exhaustive = True
    elif strategy == "greedy":
        use_exhaustive = False
    else:
        raise ValueError(f"Unknown strategy: {strategy!r}")

    if progress:
        mode = "exhaustive" if use_exhaustive else "greedy"
        print(f"  Searching {len(resolved)} items, {item_count} slots "
              f"({mode} mode)...", file=sys.stderr, flush=True)

    if use_exhaustive:
        return _exhaustive_search(
            champion, target, resolved, item_count, time_limit,
            rune, damage_modifiers, r_active, top_n, progress,
        )
    else:
        return _greedy_search(
            champion, target, resolved, item_count, time_limit,
            rune, damage_modifiers, r_active, top_n, progress,
        )
