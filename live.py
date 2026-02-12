"""Real-time Fiora damage calculator using the Live Client Data API.

Polls https://127.0.0.1:2999 during a League of Legends game to read
your Fiora's stats, items, runes, and ability ranks, then computes
damage against a target (auto-estimated from enemy data or manual).

Usage:
    python live.py                                  # auto-detect, default target
    python live.py --target Darius                  # auto-estimate Darius stats
    python live.py --target-armor 120 --target-hp 3000  # manual target
    python live.py --target Darius --target-armor 150   # auto + override armor
    python live.py --time 5                         # include DPS optimizer (5s)
    python live.py --interval 3                     # poll every 3 seconds
"""

import argparse
import io
import os
import sys
import time
from contextlib import redirect_stdout

from lol_champions import Fiora, Target, calculate_damage, optimize_dps
from lol_champions.runes import (
    PressTheAttack, Conqueror, HailOfBlades, GraspOfTheUndying,
    LastStand, CoupDeGrace, CutDown,
)
from lol_champions.items import SpearOfShojin
from lol_champions.live_client import (
    is_game_active, get_active_player, get_player_list, get_game_stats,
)
from lol_champions.data_dragon import DataDragon

# ─── Rune ID mappings ─────────────────────────────────────────────────
KEYSTONE_MAP = {
    8005: ("pta", PressTheAttack),
    8010: ("conqueror", Conqueror),
    9923: ("hob", HailOfBlades),
    8437: ("grasp", GraspOfTheUndying),
}

MINOR_RUNE_MAP = {
    8299: "last_stand",
    8014: "coup_de_grace",
    8017: "cut_down",
}

# ─── Item IDs with modeled passives ───────────────────────────────────
SHOJIN_ITEM_ID = 3161

# ─── Rune stat shard HP estimation ───────────────────────────────────
# The Live Client API doesn't expose enemy stat shards.  On first
# detection of a target we ask the user for their actual HP, then
# deduce which shard combo they're running so it scales correctly
# as they level up.
#
# Row 2 (Flex):    0 HP (adaptive / movespeed)  OR  scaling +10-180
# Row 3 (Defense): 0 HP (tenacity)  OR  +65 flat  OR  scaling +10-180
_SHARD_COMBOS = [
    ("no HP shards",       lambda lvl: 0),
    ("+65 flat",           lambda lvl: 65),
    ("1x scaling",         lambda lvl: 10 + 10 * (lvl - 1)),
    ("scaling + flat 65",  lambda lvl: 75 + 10 * (lvl - 1)),
    ("2x scaling",         lambda lvl: 20 + 20 * (lvl - 1)),
]


def _match_shard_combo(residual_hp: float, level: int) -> tuple:
    """Find the shard combo whose HP best explains the residual.

    Returns (combo_index, extra_flat_hp) where extra_flat_hp is the
    unexplained remainder (champion passives, Overgrowth, etc.).
    """
    best_idx = 0
    best_extra = residual_hp
    for i, (_, hp_func) in enumerate(_SHARD_COMBOS):
        extra = residual_hp - hp_func(level)
        if abs(extra) < abs(best_extra):
            best_idx = i
            best_extra = extra
    return best_idx, round(best_extra, 1)


def _shard_hp_at_level(combo_idx: int, level: int) -> float:
    """Compute shard HP bonus for a calibrated combo at *level*."""
    return _SHARD_COMBOS[combo_idx][1](level)


def _build_fiora_from_api(player_data: dict) -> tuple:
    """Reconstruct a Fiora instance from Live Client Data API response.

    Returns:
        (fiora, bonus_as_pct, current_hp, max_hp) tuple.
        bonus_as_pct is the item AS% for the DPS optimizer.
    """
    stats = player_data["championStats"]
    abilities = player_data["abilities"]
    level = player_data["level"]

    buf = io.StringIO()
    with redirect_stdout(buf):
        fiora = Fiora()
        for _ in range(level - 1):
            fiora.level_up()

        # Level abilities to match API ranks
        for key in ("Q", "W", "E", "R"):
            rank = abilities[key].get("abilityLevel", 0)
            for _ in range(rank):
                fiora.level_ability(key)

    # Derive bonus stats: API total - base at level (before add_stats)
    bonus_ad = stats["attackDamage"] - fiora.total_AD
    bonus_ap = stats["abilityPower"] - fiora.total_AP
    bonus_hp = stats["maxHealth"] - fiora.total_HP
    bonus_ar = stats["armor"] - fiora.total_AR
    bonus_mr = stats["magicResist"] - fiora.total_MR

    # Penetration: API returns multipliers (0.65 = 35% pen)
    lethality = stats.get("physicalLethality", 0.0)
    armor_pen_pct = 1.0 - stats.get("armorPenetrationPercent", 1.0)
    magic_pen_flat = stats.get("magicPenetrationFlat", 0.0)
    magic_pen_pct = 1.0 - stats.get("magicPenetrationPercent", 1.0)

    fiora.add_stats(
        bonus_AD=max(bonus_ad, 0),
        bonus_AP=max(bonus_ap, 0),
        bonus_HP=max(bonus_hp, 0),
        bonus_AR=max(bonus_ar, 0),
        bonus_MR=max(bonus_mr, 0),
        lethality=lethality,
        armor_pen_pct=armor_pen_pct,
        magic_pen_flat=magic_pen_flat,
        magic_pen_pct=magic_pen_pct,
    )

    current_hp = stats.get("currentHealth", stats["maxHealth"])
    max_hp = stats["maxHealth"]

    # Bonus AS: derive from API AS vs base AS at level
    base_as = fiora.total_attack_speed()  # base + level scaling only
    api_as = stats.get("attackSpeed", base_as)
    if base_as > 0 and api_as > base_as:
        bonus_as_pct = (api_as / base_as - 1.0) * 100.0
    else:
        bonus_as_pct = 0.0

    return fiora, bonus_as_pct, current_hp, max_hp


def _detect_keystone(player_data: dict):
    """Detect keystone rune from API data. Returns (name, instance) or (None, None)."""
    runes = player_data.get("fullRunes", {})
    keystone = runes.get("keystone", {})
    kid = keystone.get("id", 0)
    if kid in KEYSTONE_MAP:
        name, cls = KEYSTONE_MAP[kid]
        return name, cls()
    return None, None


def _detect_minor_runes(player_data: dict) -> set:
    """Return set of detected minor rune keys ('last_stand', 'coup_de_grace', 'cut_down')."""
    runes = player_data.get("fullRunes", {})
    detected = set()
    for rune in runes.get("generalRunes", []):
        rid = rune.get("id", 0)
        if rid in MINOR_RUNE_MAP:
            detected.add(MINOR_RUNE_MAP[rid])
    return detected


def _detect_items(player_data: dict, ddragon: DataDragon | None) -> tuple:
    """Detect item passives and collect item names.

    Returns:
        (items_list, item_names, has_shojin, bonus_as_from_items)
    """
    items_list = []
    item_names = []
    has_shojin = False
    bonus_as = 0.0

    # Active player data has items in the playerlist, not in activeplayer
    # We'll call this with the player's entry from playerlist
    return items_list, item_names, has_shojin, bonus_as


def _detect_items_from_playerlist(player_entry: dict, ddragon: DataDragon | None) -> tuple:
    """Detect items from a playerlist entry.

    Returns:
        (items_list, item_names, has_shojin, bonus_as_from_items)
    """
    items_list = []
    item_names = []
    has_shojin = False
    bonus_as = 0.0

    for item in player_entry.get("items", []):
        iid = item.get("itemID", 0)
        name = item.get("displayName", "?")
        item_names.append(name)

        if iid == SHOJIN_ITEM_ID:
            has_shojin = True
            items_list.append(SpearOfShojin(stacks=0))

        if ddragon:
            istats = ddragon.item_stats(iid)
            bonus_as += istats.get("attack_speed_pct", 0)

    return items_list, item_names, has_shojin, bonus_as


def _build_target(args, enemy_entry: dict | None, ddragon: DataDragon | None,
                   calibration: dict | None = None) -> tuple:
    """Build Target from enemy data + manual overrides + calibration.

    Returns:
        (target, target_label) tuple.
    """
    target_hp = args.target_hp
    target_armor = args.target_armor
    target_mr = args.target_mr
    label = "Manual"

    # Auto-estimate from enemy if available
    if enemy_entry and ddragon:
        champ_name = enemy_entry.get("championName", "")
        level = enemy_entry.get("level", 1)
        item_ids = [it["itemID"] for it in enemy_entry.get("items", [])]

        try:
            # Base + items only (no shard guess)
            auto_target = ddragon.estimate_target(champ_name, level, item_ids)

            # Add calibrated shard HP if available
            bonus_hp = 0.0
            shard_label = "uncalibrated"
            if calibration and champ_name in calibration:
                cal = calibration[champ_name]
                bonus_hp = _shard_hp_at_level(cal["combo_idx"], level) + cal["extra_hp"]
                shard_label = _SHARD_COMBOS[cal["combo_idx"]][0]

            if args.target_hp is None:
                target_hp = round(auto_target.max_hp + bonus_hp, 1)
            if args.target_armor is None:
                target_armor = round(auto_target.armor, 1)
            if args.target_mr is None:
                target_mr = round(auto_target.mr, 1)
            label = f"{champ_name} (Lv{level}, {shard_label})"
        except ValueError:
            label = f"{champ_name}? (unknown)"

    # Fallback defaults
    if target_hp is None:
        target_hp = 2000.0
    if target_armor is None:
        target_armor = 80.0
    if target_mr is None:
        target_mr = 50.0

    return Target(max_hp=target_hp, armor=target_armor, mr=target_mr), label


def _find_enemy(player_list: list, active_name: str, target_name: str | None) -> dict | None:
    """Find an enemy player entry from the playerlist."""
    # Find active player's team
    my_team = None
    for p in player_list:
        rid = p.get("riotId", "") or p.get("summonerName", "")
        if rid == active_name or p.get("riotIdGameName", "") == active_name:
            my_team = p.get("team")
            break

    enemies = [p for p in player_list if p.get("team") != my_team] if my_team else []

    if not enemies:
        return None

    if target_name:
        lower = target_name.lower()
        for e in enemies:
            if e.get("championName", "").lower() == lower:
                return e

    # Default: first enemy (typically top lane opponent)
    return enemies[0]


def _find_my_entry(player_list: list, active_name: str) -> dict | None:
    """Find our own entry in the playerlist (for item detection)."""
    for p in player_list:
        rid = p.get("riotId", "") or p.get("summonerName", "")
        if rid == active_name or p.get("riotIdGameName", "") == active_name:
            return p
    return None


def _build_modifiers(fiora, target, minor_runes: set,
                     current_hp: float, max_hp: float) -> list:
    """Build damage_modifiers list from detected minor runes."""
    mods = []

    if "last_stand" in minor_runes:
        missing_pct = (1.0 - current_hp / max_hp) * 100.0 if max_hp > 0 else 0.0
        ls = LastStand()
        amp = ls.damage_amp(missing_pct)
        if amp > 0:
            mods.append({"name": "Last Stand", "amp": round(amp, 4)})

    if "cut_down" in minor_runes:
        cd = CutDown()
        amp = cd.damage_amp(target.max_hp, fiora.total_HP)
        if amp > 0:
            mods.append({"name": "Cut Down", "amp": round(amp, 4)})

    # Coup de Grace: we don't know enemy current HP from API,
    # so we can't auto-calculate. Skip unless we add manual input.

    return mods


def _compute_damage(fiora, target, mods, items_list, has_shojin):
    """Compute single-ability damages. Returns dict of results."""
    results = {}

    # Shojin static amp for single-ability mode
    shojin_mod = None
    if has_shojin:
        for item in items_list:
            if isinstance(item, SpearOfShojin) and item.damage_amp() > 0:
                shojin_mod = item.modifier_dict()

    # Q
    q_data = fiora.Q()
    if "error" not in q_data:
        q_mods = mods + ([shojin_mod] if shojin_mod else [])
        q_dmg = calculate_damage(q_data, target, champion=fiora, damage_modifiers=q_mods)
        results["Q"] = (q_dmg["total_damage"], "physical")

    # W
    w_data = fiora.W()
    if "error" not in w_data:
        w_mods = mods + ([shojin_mod] if shojin_mod else [])
        w_dmg = calculate_damage(w_data, target, champion=fiora, damage_modifiers=w_mods)
        results["W"] = (w_dmg["total_damage"], "magic")

    # E (crit)
    e_data = fiora.E()
    if "error" not in e_data:
        e_mods = mods + ([shojin_mod] if shojin_mod else [])
        e_dmg = calculate_damage(e_data, target, champion=fiora, damage_modifiers=e_mods)
        results["E crit"] = (e_dmg["total_damage"], "physical")

    # Passive (vital)
    passive_mods = mods + ([shojin_mod] if shojin_mod else [])
    passive_data = fiora.passive(target_max_hp=target.max_hp)
    passive_dmg = calculate_damage(passive_data, target, champion=fiora,
                                   damage_modifiers=passive_mods)
    results["Vital"] = (passive_dmg["total_damage"], "true")
    results["_vital_heal"] = passive_data["heal"]

    # AA
    aa_data = fiora.auto_attack()
    aa_dmg = calculate_damage(aa_data, target, champion=fiora, damage_modifiers=mods)
    results["AA"] = (aa_dmg["total_damage"], "physical")

    return results


def _format_time(seconds: float) -> str:
    """Format game time as mm:ss."""
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m:02d}:{s:02d}"


def _display(fiora, target, target_label, keystone_name, minor_runes,
             current_hp, max_hp, item_names, damages, game_time,
             dps_result=None):
    """Clear screen and print formatted damage summary."""
    # Clear screen
    os.system('cls' if os.name == 'nt' else 'clear')

    hp_pct = current_hp / max_hp * 100 if max_hp > 0 else 100
    as_val = fiora.total_attack_speed()

    # Header
    print(f"\033[1m{'=' * 56}\033[0m")
    print(f"\033[1m  Fiora Live Damage\033[0m   ({_format_time(game_time)} game time)")
    print(f"\033[1m{'=' * 56}\033[0m")

    # Champion info
    q = fiora.Q_ability.current_level
    w = fiora.W_ability.current_level
    e = fiora.E_ability.current_level
    r = fiora.R_ability.current_level
    print(f"  Level {fiora.level} | Q{q} W{w} E{e} R{r} | "
          f"AD: {fiora.total_AD:.0f} | AS: {as_val:.2f}")

    # Rune info
    rune_parts = []
    if keystone_name:
        rune_parts.append(keystone_name.replace("_", " ").title())
    for mr in sorted(minor_runes):
        rune_parts.append(mr.replace("_", " ").title())
    if rune_parts:
        print(f"  Runes: {', '.join(rune_parts)}")

    # HP
    print(f"  HP: {current_hp:.0f}/{max_hp:.0f} ({hp_pct:.0f}%)")

    # Items
    if item_names:
        items_str = ", ".join(item_names[:6])
        print(f"  Items: {items_str}")

    print()

    # Target
    print(f"  Target: {target_label}")
    print(f"  Armor: {target.armor:.0f} | MR: {target.mr:.0f} | HP: {target.max_hp:.0f}")
    print(f"{'-' * 56}")

    # Damage values
    for name in ("Q", "E crit", "Vital", "AA", "W"):
        if name in damages:
            dmg, dtype = damages[name]
            color = {"physical": "\033[33m", "magic": "\033[36m", "true": "\033[37m"}.get(dtype, "")
            reset = "\033[0m"
            print(f"  {name:<10} {color}{dmg:>8.1f}  {dtype}{reset}")

    if "_vital_heal" in damages:
        print(f"  {'Vital heal':<10} {damages['_vital_heal']:>8.1f}  hp")

    # DPS
    if dps_result:
        print(f"{'-' * 56}")
        total = dps_result.get("total_damage", 0)
        dps = dps_result.get("dps", 0)
        seq = dps_result.get("sequence", "")
        print(f"  {dps_result.get('time_limit', '?')}s DPS: {dps:.0f} | Total: {total:.0f}")
        if seq:
            # Truncate long sequences
            if len(seq) > 48:
                seq = seq[:45] + "..."
            print(f"  Seq: {seq}")

    print(f"\033[1m{'=' * 56}\033[0m")
    print("  Ctrl+C to stop")


def main():
    p = argparse.ArgumentParser(
        description="Real-time Fiora damage calculator (Live Client Data API).",
    )
    p.add_argument("--target", type=str, default=None,
                   help="Enemy champion name to auto-track (e.g. Darius)")
    p.add_argument("--target-hp", type=float, default=None,
                   help="Manual target HP override")
    p.add_argument("--target-armor", type=float, default=None,
                   help="Manual target armor override")
    p.add_argument("--target-mr", type=float, default=None,
                   help="Manual target MR override")
    p.add_argument("--interval", type=float, default=2.0,
                   help="Poll interval in seconds (default: 2)")
    p.add_argument("--time", type=float, default=None,
                   help="Also run DPS optimizer with this time window")
    args = p.parse_args()

    # Wait for game
    print("Waiting for game to start...")
    while not is_game_active():
        time.sleep(5)
    print("Game detected! Loading Data Dragon...")

    # Load Data Dragon
    ddragon = None
    try:
        ddragon = DataDragon()
        print(f"Data Dragon v{ddragon.version} loaded.")
    except Exception as e:
        print(f"Warning: Could not load Data Dragon ({e}). Target auto-estimation disabled.")

    # Calibration cache: {champ_name: {"combo_idx": int, "extra_hp": float}}
    target_calibration = {}

    # Main poll loop
    try:
        while True:
            if not is_game_active():
                print("\nGame ended. Waiting for next game...")
                target_calibration.clear()
                while not is_game_active():
                    time.sleep(5)
                print("Game detected!")

            try:
                player_data = get_active_player()
                player_list = get_player_list()
                game_stats = get_game_stats()
            except Exception:
                time.sleep(args.interval)
                continue

            game_time = game_stats.get("gameTime", 0.0)

            # Get active player name for team detection
            active_name = player_data.get("riotId", "") or player_data.get("riotIdGameName", "")

            # Build Fiora from API data
            fiora, bonus_as_api, current_hp, max_hp = _build_fiora_from_api(player_data)

            # Find our entry in playerlist for item detection
            my_entry = _find_my_entry(player_list, active_name)
            items_list, item_names, has_shojin, bonus_as_items = (
                _detect_items_from_playerlist(my_entry, ddragon)
                if my_entry else ([], [], False, 0.0)
            )

            # Use item-derived bonus AS if available, else API-derived
            bonus_as = bonus_as_items if bonus_as_items > 0 else bonus_as_api

            # Find enemy target
            enemy = _find_enemy(player_list, active_name, args.target)

            # Calibrate new targets: ask user for actual HP once per champion
            if enemy and ddragon:
                champ_name = enemy.get("championName", "")
                level = enemy.get("level", 1)
                if champ_name and champ_name not in target_calibration:
                    item_ids = [it["itemID"] for it in enemy.get("items", [])]
                    try:
                        raw = ddragon.estimate_target(champ_name, level, item_ids)
                        print(f"\n  New target detected: {champ_name} (Lv{level})")
                        print(f"  Base+items HP estimate: {raw.max_hp:.0f}")
                        hp_input = input(f"  Enter {champ_name}'s actual max HP: ").strip()
                        actual_hp = float(hp_input)
                        residual = actual_hp - raw.max_hp
                        combo_idx, extra = _match_shard_combo(residual, level)
                        target_calibration[champ_name] = {
                            "combo_idx": combo_idx, "extra_hp": extra,
                        }
                        combo_name = _SHARD_COMBOS[combo_idx][0]
                        msg = f"  -> Shards: {combo_name}"
                        if abs(extra) > 5:
                            msg += f" + {extra:.0f} extra HP (passives/runes)"
                        print(msg)
                        time.sleep(1.5)
                    except (ValueError, EOFError):
                        # Bad input or skipped — fall back to common default
                        target_calibration[champ_name] = {
                            "combo_idx": 3, "extra_hp": 0,  # scaling + flat 65
                        }
                        print("  -> Using default estimate (scaling + flat 65)")
                        time.sleep(1)

            target, target_label = _build_target(args, enemy, ddragon, target_calibration)

            # Detect runes
            keystone_name, keystone = _detect_keystone(player_data)
            minor_runes = _detect_minor_runes(player_data)

            # Build damage modifiers
            mods = _build_modifiers(fiora, target, minor_runes, current_hp, max_hp)

            # Compute damages
            damages = _compute_damage(fiora, target, mods, items_list, has_shojin)

            # DPS optimizer (optional, expensive)
            dps_result = None
            if args.time:
                try:
                    rune_for_dps = keystone
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        dps_result = optimize_dps(
                            champion=fiora,
                            target=target,
                            time_limit=args.time,
                            rune=rune_for_dps,
                            bonus_as=bonus_as,
                            damage_modifiers=mods if mods else None,
                            items=items_list if items_list else None,
                        )
                except Exception:
                    pass

            # Display
            _display(
                fiora, target, target_label, keystone_name, minor_runes,
                current_hp, max_hp, item_names, damages, game_time,
                dps_result,
            )

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
