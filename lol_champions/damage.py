"""Damage calculation engine following League of Legends formulas.

All formulas sourced from https://wiki.leagueoflegends.com/en-us/
"""

from typing import Dict, Any


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
) -> Dict[str, Any]:
    """Calculate post-mitigation damage for an ability against a target.

    Reads 'raw_damage' and 'damage_type' from ability_data dict.
    Reads penetration stats from champion if provided.
    Applies mitigation from target's armor/MR.
    Applies optional damage_amp as a multiplier.

    Args:
        ability_data: Dict returned by champion ability method (must have
                      'raw_damage' and 'damage_type' keys)
        target: Target instance with armor/mr stats
        champion: Optional Champion with penetration stats (lethality,
                  armor_pen_pct, magic_pen_flat, magic_pen_pct)
        damage_amp: Fractional damage amplification (0.08 = 8% more damage)
        flat_reduction: Additional flat resistance reduction
        pct_reduction: Additional percentage resistance reduction

    Returns:
        Dict with: raw_damage, damage_type, effective_resistance,
        post_mitigation_damage, damage_reduction_pct, damage_amp, total_damage

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

    # Apply damage amplification (e.g., PtA exposure)
    total_damage = round(post_mitigation * (1.0 + damage_amp), 2)

    return {
        "raw_damage": raw_damage,
        "damage_type": damage_type,
        "effective_resistance": eff_resistance,
        "post_mitigation_damage": post_mitigation,
        "damage_reduction_pct": reduction_pct,
        "damage_amp": damage_amp,
        "total_damage": total_damage,
    }
