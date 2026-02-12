"""Damage calculation engine following League of Legends formulas.

All formulas sourced from https://wiki.leagueoflegends.com/en-us/
"""

from typing import Dict, Any, List


# Type alias for dicts returned by champion ability methods and rune procs
AbilityData = Dict[str, Any]


# ─── LOW-LEVEL FUNCTIONS (pure math, no object dependencies) ───


def effective_resistance(
    resistance: float,
    flat_reduction: float = 0.0,
    pct_reduction: float = 0.0,
    pct_penetration: float = 0.0,
    flat_penetration: float = 0.0,
) -> float:
    """Calculate effective resistance after penetration/reduction.

    Applies the LoL penetration order of operations:
      1. Flat reduction (CAN go negative)
      2. Percentage reduction
      3. Percentage penetration (only if resistance > 0)
      4. Flat penetration / lethality (only if resistance > 0; cannot reduce below 0)

    Args:
        resistance: Total armor or MR
        flat_reduction: Flat armor/MR reduction (e.g., from abilities)
        pct_reduction: Percentage reduction as decimal (0.30 = 30%)
        pct_penetration: Percentage penetration as decimal (0.35 = 35%)
        flat_penetration: Flat penetration / lethality value

    Returns:
        Effective resistance value (can be negative from reductions)
    """
    # Step 1: Flat reduction
    total = resistance - flat_reduction

    # Step 2: Percentage reduction
    total = total * (1.0 - pct_reduction)

    # Steps 3-4: Penetration only applies to positive resistance
    if total > 0:
        # Step 3: Percentage penetration
        total = total * (1.0 - pct_penetration)
        # Step 4: Flat penetration (cannot reduce below 0)
        total = max(0.0, total - flat_penetration)

    return round(total, 2)


def damage_after_mitigation(raw_damage: float, resistance: float) -> float:
    """Apply the LoL damage reduction formula.

    Formula:
      - If resistance >= 0: damage * (100 / (100 + resistance))
      - If resistance < 0:  damage * (2 - 100 / (100 - resistance))

    Args:
        raw_damage: Pre-mitigation damage value
        resistance: Effective armor or MR (after pen/reduction)

    Returns:
        Post-mitigation damage, rounded to 2 decimal places
    """
    if resistance >= 0:
        multiplier = 100.0 / (100.0 + resistance)
    else:
        multiplier = 2.0 - 100.0 / (100.0 - resistance)

    return round(raw_damage * multiplier, 2)


def resolve_adaptive_type(bonus_ad: float, bonus_ap: float) -> str:
    """Determine adaptive damage type based on higher bonus stat.

    Args:
        bonus_ad: Champion's bonus attack damage
        bonus_ap: Champion's bonus ability power

    Returns:
        'physical' if bonus AD >= bonus AP, else 'magic'
    """
    return "physical" if bonus_ad >= bonus_ap else "magic"


# ─── HIGH-LEVEL CONVENIENCE FUNCTION ───


def calculate_damage(
    ability_data: AbilityData,
    target,
    champion=None,
    damage_amp: float = 0.0,
    flat_reduction: float = 0.0,
    pct_reduction: float = 0.0,
    damage_modifiers: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Calculate post-mitigation damage for an ability against a target.

    Reads 'raw_damage' and 'damage_type' from ability_data dict.
    Reads penetration stats from champion if provided.
    Applies mitigation from target's armor/MR.
    Applies optional damage_amp and damage_modifiers as multipliers.

    Damage modifiers (Last Stand, Shojin, Coup de Grace, etc.) stack
    multiplicatively with each other and with damage_amp:
        total = post_mitigation × (1 + damage_amp) × Π(1 + mod["amp"])

    Args:
        ability_data: Dict returned by champion ability method (must have
                      'raw_damage' and 'damage_type' keys)
        target: Target instance with armor/mr stats
        champion: Optional Champion with penetration stats (lethality,
                  armor_pen_pct, magic_pen_flat, magic_pen_pct)
        damage_amp: Fractional damage amplification (0.08 = 8% more damage)
        flat_reduction: Additional flat resistance reduction
        pct_reduction: Additional percentage resistance reduction
        damage_modifiers: List of {"name": str, "amp": float} dicts.
                          Each amp is a decimal (0.11 = 11%). Applied
                          multiplicatively.

    Returns:
        Dict with: raw_damage, damage_type, effective_resistance,
        post_mitigation_damage, damage_reduction_pct, damage_amp,
        damage_modifiers, total_amp_multiplier, total_damage

    Raises:
        ValueError: If ability_data is missing required keys
    """
    if "raw_damage" not in ability_data:
        raise ValueError(
            "ability_data must contain 'raw_damage' key. "
            "Got keys: " + str(list(ability_data.keys()))
        )

    raw_damage = ability_data["raw_damage"]
    damage_type = ability_data.get("damage_type", "physical")

    # Resolve adaptive damage type
    if damage_type == "adaptive" and champion is not None:
        damage_type = resolve_adaptive_type(champion.bonus_AD, champion.bonus_AP)
    elif damage_type == "adaptive":
        damage_type = "physical"

    # True damage bypasses everything
    if damage_type == "true":
        post_mitigation = raw_damage
        eff_resistance = 0.0
        reduction_pct = 0.0
    else:
        # Determine which resistance applies
        if damage_type == "physical":
            resistance = target.armor
            pct_pen = getattr(champion, 'armor_pen_pct', 0.0) if champion else 0.0
            flat_pen = getattr(champion, 'lethality', 0.0) if champion else 0.0
        else:  # magic
            resistance = target.mr
            pct_pen = getattr(champion, 'magic_pen_pct', 0.0) if champion else 0.0
            flat_pen = getattr(champion, 'magic_pen_flat', 0.0) if champion else 0.0

        eff_resistance = effective_resistance(
            resistance,
            flat_reduction=flat_reduction,
            pct_reduction=pct_reduction,
            pct_penetration=pct_pen,
            flat_penetration=flat_pen,
        )

        post_mitigation = damage_after_mitigation(raw_damage, eff_resistance)
        reduction_pct = round(
            (1.0 - post_mitigation / raw_damage) * 100, 2
        ) if raw_damage > 0 else 0.0

    # Apply damage amplification (PtA exposure, Last Stand, Shojin, etc.)
    # All sources stack multiplicatively.
    multiplier = 1.0 + damage_amp
    mods = damage_modifiers or []
    for mod in mods:
        multiplier *= (1.0 + mod.get("amp", 0.0))
    total_damage = round(post_mitigation * multiplier, 2)

    return {
        "raw_damage": raw_damage,
        "damage_type": damage_type,
        "effective_resistance": eff_resistance,
        "post_mitigation_damage": post_mitigation,
        "damage_reduction_pct": reduction_pct,
        "damage_amp": damage_amp,
        "damage_modifiers": mods,
        "total_amp_multiplier": round(multiplier, 4),
        "total_damage": total_damage,
    }


# ─── COMBO CALCULATOR ───

# Steps that count as on-hit (trigger PtA stacks, Grasp proc).
# Fiora Q applies on-hit effects in LoL, so it counts.
ON_HIT_STEPS = {"AA", "Q", "E"}


def _resolve_step(champion, step: str, target_max_hp: float) -> dict:
    """Map a combo step name to an ability_data dict."""
    step = step.upper()
    if step == "AA":
        return champion.auto_attack()
    if step == "PASSIVE":
        return champion.passive(target_max_hp=target_max_hp)
    if step in ("Q", "W", "E"):
        return getattr(champion, step)()
    return {"error": f"Unknown step: {step}"}


def calculate_combo(
    champion,
    target,
    steps: List[str],
    rune=None,
    damage_modifiers: List[Dict[str, Any]] = None,
    items: list = None,
) -> Dict[str, Any]:
    """Calculate total damage from a combo sequence.

    Tracks rune state through the combo:
    - PtA: procs on 3rd on-hit, then 8% damage amp on all subsequent steps.
    - Conqueror: +2 stacks per damaging step (melee). At 12 stacks grants
      bonus AD and heals 8% of post-mitigation damage.
    - Grasp: first on-hit deals bonus magic damage and heals.
    - HoB: noted but no per-step damage modification.

    Item passives tracked per-step:
    - Spear of Shojin: stacks on ability damage, amplifies ability/proc damage.

    Static damage modifiers (Last Stand, Coup de Grace, etc.) apply to every
    step multiplicatively.

    On-hit steps (stack PtA / trigger Grasp): AA, Q, E.

    Args:
        champion: Champion instance (e.g. Fiora)
        target: Target instance
        steps: List of step names, e.g. ["AA", "Q", "passive", "AA", "E"]
        rune: Optional rune instance
        damage_modifiers: Static modifiers applied every step
                          [{"name": str, "amp": float}, ...]
        items: List of item instances (e.g. [SpearOfShojin(stacks=0)])

    Returns:
        Dict with per-step breakdown, totals, and healing.
    """
    from .runes import PressTheAttack, Conqueror, GraspOfTheUndying
    from .items import SpearOfShojin

    # Rune state
    pta_hits = 0
    pta_exposed = False
    conq_stacks = 0
    conq_bonus_ad = 0.0
    grasp_available = True

    # Item state
    shojin = None
    if items:
        for item in items:
            if isinstance(item, SpearOfShojin):
                shojin = SpearOfShojin(stacks=item.stacks)  # copy

    # Static modifiers (Last Stand, Coup de Grace, etc.)
    static_mods = damage_modifiers or []

    step_results = []
    total_healing = 0.0

    try:
        for step_name in steps:
            step = step_name.upper()
            is_on_hit = step in ON_HIT_STEPS

            # --- Conqueror: apply bonus AD once fully stacked ---
            if rune and isinstance(rune, Conqueror) and conq_stacks == rune.max_stacks and conq_bonus_ad == 0.0:
                bonus = rune.stat_bonus(champion.level, stacks=rune.max_stacks, adaptive="ad")
                conq_bonus_ad = bonus["bonus_AD"]
                champion.add_stats(bonus_AD=conq_bonus_ad)

            # Resolve step
            ability_data = _resolve_step(champion, step, target.max_hp)
            if "error" in ability_data:
                step_results.append({"step": step, "error": ability_data["error"]})
                continue

            # Damage amp from PtA exposure
            damage_amp = 0.08 if pta_exposed else 0.0

            # Build per-step modifiers: static + Shojin (if applicable)
            # Shojin: triggering ability does NOT benefit from its own stack.
            # Apply current stacks first, then grant the new stack after.
            step_mods = list(static_mods)  # copy
            if shojin and SpearOfShojin.is_amplified(step):
                step_mods.append(shojin.modifier_dict())

            dmg = calculate_damage(
                ability_data, target, champion=champion,
                damage_amp=damage_amp, damage_modifiers=step_mods,
            )

            # Grant Shojin stack AFTER damage is calculated
            if shojin and SpearOfShojin.grants_stack(step):
                shojin.add_stack()

            entry = {
                "step": step,
                "raw_damage": dmg["raw_damage"],
                "damage_type": dmg["damage_type"],
                "post_mitigation": dmg["total_damage"],
                "amp_multiplier": dmg["total_amp_multiplier"],
            }
            if shojin:
                entry["shojin_stacks"] = shojin.stacks

            # Collect healing from passive
            if step == "PASSIVE":
                heal = ability_data.get("heal", 0)
                entry["heal"] = heal
                total_healing += heal

            # --- PtA tracking ---
            if rune and isinstance(rune, PressTheAttack) and is_on_hit:
                pta_hits += 1
                if pta_hits == 3 and not pta_exposed:
                    proc = rune.proc_damage(champion.level, champion.bonus_AD, champion.bonus_AP)
                    proc_dmg = calculate_damage(proc, target, champion=champion)
                    entry["pta_proc"] = proc_dmg["total_damage"]
                    pta_exposed = True

            # --- Conqueror tracking ---
            if rune and isinstance(rune, Conqueror) and step != "PASSIVE":
                conq_stacks = min(conq_stacks + 2, rune.max_stacks)
                entry["conq_stacks"] = conq_stacks
                # Heal at max stacks
                if conq_stacks == rune.max_stacks:
                    heal = rune.healing(dmg["post_mitigation_damage"], is_melee=champion.is_melee)
                    entry["conq_heal"] = heal["heal"]
                    total_healing += heal["heal"]

            # --- Grasp tracking ---
            if rune and isinstance(rune, GraspOfTheUndying) and is_on_hit and grasp_available:
                proc = rune.proc_damage(champion.total_HP, is_melee=champion.is_melee)
                proc_dmg = calculate_damage(proc, target, champion=champion)
                heal = rune.healing(champion.total_HP, is_melee=champion.is_melee)
                entry["grasp_proc"] = proc_dmg["total_damage"]
                entry["grasp_heal"] = heal["heal"]
                total_healing += heal["heal"]
                grasp_available = False

            step_results.append(entry)

    finally:
        # Clean up temporary Conqueror bonus AD
        if conq_bonus_ad > 0:
            champion.add_stats(bonus_AD=-conq_bonus_ad)

    # Totals
    total_damage = sum(r.get("post_mitigation", 0) for r in step_results)
    rune_damage = sum(r.get("pta_proc", 0) + r.get("grasp_proc", 0) for r in step_results)

    return {
        "combo": " > ".join(s.upper() for s in steps),
        "steps": step_results,
        "total_damage": round(total_damage + rune_damage, 2),
        "total_rune_damage": round(rune_damage, 2),
        "total_healing": round(total_healing, 2),
    }
