"""CLI for Fiora damage calculations. Outputs JSON for easy parsing by Copilot/Claude.

Usage examples:
    python cli.py --level 9 --q 5 --w 1 --e 1 --r 1 --bonus-ad 50 --target-armor 80 --target-mr 50 --target-hp 2000
    python cli.py --level 9 --q 5 --bonus-ad 50 --lethality 10 --target-armor 80 --rune pta
    python cli.py --level 11 --q 5 --w 3 --e 3 --r 2 --bonus-ad 120 --armor-pen-pct 0.3 --lethality 18 --target-armor 120 --target-mr 60 --target-hp 3000 --rune conqueror
"""

import argparse
import io
import json
import sys
from contextlib import redirect_stdout

from lol_champions import Fiora, Target, calculate_damage, calculate_combo, optimize_dps
from lol_champions.runes import PressTheAttack, Conqueror, HailOfBlades, GraspOfTheUndying
from lol_champions.runes import LastStand, CoupDeGrace, CutDown
from lol_champions.items import SpearOfShojin

RUNES = {
    "pta": PressTheAttack,
    "conqueror": Conqueror,
    "hob": HailOfBlades,
    "grasp": GraspOfTheUndying,
}


def build_fiora(args) -> Fiora:
    """Create and configure a Fiora instance from CLI args, suppressing prints."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        fiora = Fiora()
        for _ in range(args.level - 1):
            fiora.level_up()
        for ability, rank in [('Q', args.q), ('W', args.w), ('E', args.e), ('R', args.r)]:
            for _ in range(rank):
                fiora.level_ability(ability)
        fiora.add_stats(
            bonus_AD=args.bonus_ad,
            bonus_AP=args.bonus_ap,
            bonus_HP=args.bonus_hp,
            bonus_AR=args.bonus_ar,
            bonus_MR=args.bonus_mr,
            lethality=args.lethality,
            armor_pen_pct=args.armor_pen_pct,
            magic_pen_flat=args.magic_pen_flat,
            magic_pen_pct=args.magic_pen_pct,
        )
    return fiora


def build_modifiers(args, fiora=None, target=None):
    """Build damage_modifiers list and items list from CLI args.

    Returns:
        (damage_modifiers, items) tuple.
    """
    mods = []
    items = []

    # Last Stand (missing HP %, 0-100)
    if args.last_stand is not None:
        rune = LastStand()
        amp = rune.damage_amp(args.last_stand)
        if amp > 0:
            mods.append({"name": "Last Stand", "amp": round(amp, 4)})

    # Coup de Grace (target HP %, 0-100)
    if args.coup_de_grace is not None:
        rune = CoupDeGrace()
        amp = rune.damage_amp(args.coup_de_grace)
        if amp > 0:
            mods.append({"name": "Coup de Grace", "amp": round(amp, 4)})

    # Cut Down (requires target_hp and champion HP)
    if args.cut_down and fiora and target:
        rune = CutDown()
        amp = rune.damage_amp(target.max_hp, fiora.total_HP)
        if amp > 0:
            mods.append({"name": "Cut Down", "amp": round(amp, 4)})

    # Spear of Shojin
    if args.shojin_stacks is not None:
        shojin = SpearOfShojin(stacks=args.shojin_stacks)
        items.append(shojin)
        # For default mode, add static amp; combo/DPS handle dynamically

    return mods, items


def compute(args):
    fiora = build_fiora(args)
    target = Target(max_hp=args.target_hp, armor=args.target_armor, mr=args.target_mr)
    mods, items_list = build_modifiers(args, fiora=fiora, target=target)

    # For default mode, Shojin amp is applied statically per ability
    shojin_mod = None
    for item in items_list:
        if isinstance(item, SpearOfShojin) and item.damage_amp() > 0:
            shojin_mod = item.modifier_dict()

    result = {
        "champion": {
            "name": "Fiora",
            "level": fiora.level,
            "total_AD": round(fiora.total_AD, 2),
            "total_AP": round(fiora.total_AP, 2),
            "total_HP": round(fiora.total_HP, 2),
            "bonus_AD": fiora.bonus_AD,
            "lethality": fiora.lethality,
            "armor_pen_pct": fiora.armor_pen_pct,
            "magic_pen_flat": fiora.magic_pen_flat,
            "magic_pen_pct": fiora.magic_pen_pct,
            "abilities": {
                "Q": fiora.Q_ability.current_level,
                "W": fiora.W_ability.current_level,
                "E": fiora.E_ability.current_level,
                "R": fiora.R_ability.current_level,
            },
        },
        "target": {"max_hp": target.max_hp, "armor": target.armor, "mr": target.mr},
        "abilities": {},
        "rune": None,
        "damage_modifiers": mods + ([shojin_mod] if shojin_mod else []),
    }

    # Abilities — Shojin applies to Q, W, E, passive but NOT to auto attacks
    for name, method in [("Q", fiora.Q), ("W", fiora.W), ("E", fiora.E)]:
        ability_mods = mods[:]
        if shojin_mod:
            ability_mods.append(shojin_mod)
        data = method()
        if "error" in data:
            result["abilities"][name] = {"error": data["error"]}
        else:
            dmg = calculate_damage(data, target, champion=fiora,
                                   damage_modifiers=ability_mods)
            result["abilities"][name] = {
                "raw_damage": dmg["raw_damage"],
                "damage_type": dmg["damage_type"],
                "post_mitigation": dmg["total_damage"],
                "effective_resistance": dmg["effective_resistance"],
                "cooldown": data.get("cooldown"),
                "amp_multiplier": dmg.get("total_amp_multiplier"),
            }

    # Passive (Shojin amplifies proc damage; Last Stand etc. apply too)
    passive_mods = mods[:]
    if shojin_mod:
        passive_mods.append(shojin_mod)
    passive_data = fiora.passive(target_max_hp=target.max_hp)
    passive_dmg = calculate_damage(passive_data, target, champion=fiora,
                                    damage_modifiers=passive_mods)
    result["abilities"]["passive"] = {
        "raw_damage": passive_dmg["raw_damage"],
        "damage_type": "true",
        "post_mitigation": passive_dmg["total_damage"],
        "heal": passive_data["heal"],
        "true_damage_percent": passive_data["true_damage_percent"],
        "amp_multiplier": passive_dmg.get("total_amp_multiplier"),
    }

    # R (healing info, no direct damage)
    r_data = fiora.R()
    if "error" in r_data:
        result["abilities"]["R"] = {"error": r_data["error"]}
    else:
        result["abilities"]["R"] = {
            "cooldown": r_data["cooldown"],
            "heal_per_tick": r_data["heal_per_tick"],
            "duration": r_data["duration"],
            "note": "R damage comes from 4x passive procs",
            "total_passive_damage": round(passive_dmg["total_damage"] * 4, 2),
        }

    # Rune
    if args.rune:
        rune_key = args.rune.lower()
        rune_cls = RUNES.get(rune_key)
        if rune_cls is None:
            result["rune"] = {"error": f"Unknown rune: {args.rune}. Options: {list(RUNES.keys())}"}
        else:
            rune = rune_cls()
            rune_out = {"name": rune.name}

            if rune_key == "pta":
                proc = rune.proc_damage(fiora.level, fiora.bonus_AD, fiora.bonus_AP)
                proc_dmg = calculate_damage(proc, target, champion=fiora)
                exposure = rune.exposure()
                q_data = fiora.Q()
                if "error" not in q_data:
                    q_exposed = calculate_damage(q_data, target, champion=fiora,
                                                 damage_amp=exposure["damage_amp"])
                    rune_out["q_with_exposure"] = q_exposed["total_damage"]
                rune_out["proc_damage"] = proc_dmg["total_damage"]
                rune_out["proc_type"] = proc_dmg["damage_type"]
                rune_out["exposure_amp"] = "8%"
                rune_out["cooldown"] = proc["cooldown"]

            elif rune_key == "conqueror":
                bonus = rune.stat_bonus(fiora.level, stacks=12, adaptive="ad")
                rune_out["max_stacks_bonus_AD"] = bonus["bonus_AD"]
                rune_out["per_stack_AD"] = bonus["per_stack_AD"]
                # Q damage with max stacks
                fiora.add_stats(bonus_AD=bonus["bonus_AD"])
                q_data = fiora.Q()
                if "error" not in q_data:
                    q_conq = calculate_damage(q_data, target, champion=fiora)
                    rune_out["q_at_max_stacks"] = q_conq["total_damage"]
                    heal = rune.healing(q_conq["post_mitigation_damage"], is_melee=True)
                    rune_out["heal_from_q"] = heal["heal"]
                fiora.add_stats(bonus_AD=-bonus["bonus_AD"])

            elif rune_key == "hob":
                bonus = rune.attack_speed_bonus(is_melee=True)
                rune_out["bonus_attack_speed"] = bonus["bonus_attack_speed"]
                rune_out["duration"] = bonus["duration"]
                rune_out["cooldown"] = bonus["cooldown"]

            elif rune_key == "grasp":
                proc = rune.proc_damage(fiora.total_HP, is_melee=True)
                proc_dmg = calculate_damage(proc, target, champion=fiora)
                heal = rune.healing(fiora.total_HP, is_melee=True)
                perm = rune.permanent_hp(is_melee=True)
                rune_out["proc_damage"] = proc_dmg["total_damage"]
                rune_out["proc_type"] = "magic"
                rune_out["heal"] = heal["heal"]
                rune_out["permanent_hp"] = perm["permanent_hp"]

            result["rune"] = rune_out

    return result


def compute_combo(args):
    fiora = build_fiora(args)
    target = Target(max_hp=args.target_hp, armor=args.target_armor, mr=args.target_mr)
    mods, items_list = build_modifiers(args, fiora=fiora, target=target)

    steps = args.combo.split()
    rune = RUNES[args.rune.lower()]() if args.rune and args.rune.lower() in RUNES else None

    combo_result = calculate_combo(
        fiora, target, steps, rune=rune,
        damage_modifiers=mods if mods else None,
        items=items_list if items_list else None,
    )

    return {
        "champion": {
            "name": "Fiora",
            "level": fiora.level,
            "total_AD": round(fiora.total_AD, 2),
            "bonus_AD": fiora.bonus_AD,
            "lethality": fiora.lethality,
        },
        "target": {"max_hp": target.max_hp, "armor": target.armor, "mr": target.mr},
        "rune": rune.name if rune else None,
        "damage_modifiers": mods,
        **combo_result,
    }


def compute_dps(args):
    fiora = build_fiora(args)
    target = Target(max_hp=args.target_hp, armor=args.target_armor, mr=args.target_mr)
    mods, items_list = build_modifiers(args, fiora=fiora, target=target)
    rune = RUNES[args.rune.lower()]() if args.rune and args.rune.lower() in RUNES else None

    result = optimize_dps(
        champion=fiora,
        target=target,
        time_limit=args.time,
        rune=rune,
        r_active=args.r_active,
        bonus_as=args.bonus_as,
        damage_modifiers=mods if mods else None,
        items=items_list if items_list else None,
    )

    result["champion"] = {
        "name": "Fiora",
        "level": fiora.level,
        "total_AD": round(fiora.total_AD, 2),
        "bonus_AD": fiora.bonus_AD,
        "attack_speed": round(fiora.total_attack_speed(extra_bonus_as_pct=args.bonus_as), 3),
        "attack_interval": round(fiora.attack_interval(extra_bonus_as_pct=args.bonus_as), 3),
    }
    result["target"] = {"max_hp": target.max_hp, "armor": target.armor, "mr": target.mr}
    result["rune"] = rune.name if rune else None
    result["damage_modifiers"] = mods

    return result


def main():
    p = argparse.ArgumentParser(
        description="Fiora damage calculator. Outputs JSON.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  python cli.py --level 9 --q 5 --bonus-ad 50 --target-armor 80
  python cli.py --level 9 --q 5 --w 1 --e 1 --r 1 --bonus-ad 50 --lethality 10 --target-armor 80 --rune pta
  python cli.py --combo "AA Q passive AA E AA" --level 9 --q 5 --e 1 --bonus-ad 50 --target-armor 80 --rune pta
  python cli.py --combo "AA Q passive AA E AA passive AA passive AA passive" --level 11 --q 5 --e 3 --r 2 --bonus-ad 120 --target-armor 100 --rune conqueror""",
    )

    # Champion
    p.add_argument("--level", type=int, default=1, help="Champion level (1-18)")
    p.add_argument("--q", type=int, default=0, help="Q rank (0-5)")
    p.add_argument("--w", type=int, default=0, help="W rank (0-5)")
    p.add_argument("--e", type=int, default=0, help="E rank (0-5)")
    p.add_argument("--r", type=int, default=0, help="R rank (0-3)")

    # Bonus stats
    p.add_argument("--bonus-ad", type=float, default=0, help="Bonus AD from items")
    p.add_argument("--bonus-ap", type=float, default=0, help="Bonus AP from items")
    p.add_argument("--bonus-hp", type=float, default=0, help="Bonus HP from items")
    p.add_argument("--bonus-ar", type=float, default=0, help="Bonus armor from items")
    p.add_argument("--bonus-mr", type=float, default=0, help="Bonus MR from items")

    # Penetration
    p.add_argument("--lethality", type=float, default=0, help="Lethality (flat armor pen)")
    p.add_argument("--armor-pen-pct", type=float, default=0, help="Armor pen %% as decimal (0.3 = 30%%)")
    p.add_argument("--magic-pen-flat", type=float, default=0, help="Flat magic penetration")
    p.add_argument("--magic-pen-pct", type=float, default=0, help="Magic pen %% as decimal (0.4 = 40%%)")

    # Target
    p.add_argument("--target-hp", type=float, default=2000, help="Target max HP (default: 2000)")
    p.add_argument("--target-armor", type=float, default=80, help="Target armor (default: 80)")
    p.add_argument("--target-mr", type=float, default=50, help="Target MR (default: 50)")

    # Rune
    p.add_argument("--rune", type=str, default=None,
                   help="Keystone rune: pta, conqueror, hob, grasp")

    # Combo
    p.add_argument("--combo", type=str, default=None,
                   help="Combo sequence, e.g. \"AA Q passive AA E AA\". "
                        "Steps: AA, Q, W, E, passive")

    # DPS optimizer
    p.add_argument("--time", type=float, default=None,
                   help="DPS optimize: find max damage in T seconds (e.g. --time 5)")
    p.add_argument("--bonus-as", type=float, default=0,
                   help="Bonus attack speed %% from items (e.g. 35 for 35%%)")
    p.add_argument("--r-active", action="store_true", default=False,
                   help="R is active (4 vitals available immediately)")
    # Damage modifiers (minor runes)
    p.add_argument("--last-stand", type=float, default=None, metavar="MISSING_HP_PCT",
                   help="Last Stand: your missing HP %% (0-100). "
                        "E.g. 70 = 30%% current HP → 11%% amp (max)")
    p.add_argument("--coup-de-grace", type=float, default=None, metavar="TARGET_HP_PCT",
                   help="Coup de Grace: target current HP %%. "
                        "8%% amp if target < 40%% HP")
    p.add_argument("--cut-down", action="store_true", default=False,
                   help="Cut Down: auto-calculated from target/champion HP")

    # Item passives
    p.add_argument("--shojin-stacks", type=int, default=None, metavar="N",
                   help="Spear of Shojin stacks (0-4). "
                        "3%% per stack on ability/proc damage")
    args = p.parse_args()
    if args.time:
        output = compute_dps(args)
    elif args.combo:
        output = compute_combo(args)
    else:
        output = compute(args)
    json.dump(output, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
