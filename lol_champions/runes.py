"""Keystone rune calculators for League of Legends.

All values sourced from https://wiki.leagueoflegends.com/en-us/
Rune proc dicts include 'raw_damage' and 'damage_type' keys so they can
be passed directly to calculate_damage().
"""

from dataclasses import dataclass
from typing import Dict, Any


def _level_scale(min_val: float, max_val: float, level: int, max_level: int = 18) -> float:
    """Linear interpolation for level-based rune scaling.

    LoL rune scaling uses levels 1-18 regardless of champion max level.
    Levels above 18 are clamped to the level-18 value.

    Args:
        min_val: Value at level 1
        max_val: Value at level 18
        level: Current champion level
        max_level: Level at which max_val is reached (default 18)

    Returns:
        Interpolated value, rounded to 2 decimal places
    """
    clamped = max(1, min(level, max_level))
    if max_level <= 1:
        return round(min_val, 2)
    value = min_val + (max_val - min_val) * (clamped - 1) / (max_level - 1)
    return round(value, 2)


@dataclass
class PressTheAttack:
    """Press the Attack (Precision keystone).

    After hitting an enemy champion with 3 consecutive basic attacks,
    deal bonus adaptive damage and expose the target to increased damage.

    Usage:
        pta = PressTheAttack()
        proc = pta.proc_damage(champion_level=9)
        exposure = pta.exposure()
    """
    name: str = "Press the Attack"
    keystone_type: str = "Precision"

    def proc_damage(self, champion_level: int, bonus_ad: float = 0.0, bonus_ap: float = 0.0) -> Dict[str, Any]:
        """Calculate the proc damage when 3rd basic attack lands.

        Args:
            champion_level: Current champion level (1-18+)
            bonus_ad: Champion's bonus AD (for adaptive type resolution)
            bonus_ap: Champion's bonus AP (for adaptive type resolution)

        Returns:
            Dict with raw_damage, damage_type, cooldown
        """
        damage = _level_scale(40.0, 174.12, champion_level)
        adaptive = "physical" if bonus_ad >= bonus_ap else "magic"
        return {
            "raw_damage": damage,
            "damage_type": adaptive,
            "cooldown": 6.0,
            "description": f"3-hit proc: {damage} {adaptive} damage",
        }

    def exposure(self) -> Dict[str, Any]:
        """The Exposed debuff applied after proc.

        Returns:
            Dict with damage_amp (0.08 = 8%), duration
        """
        return {
            "damage_amp": 0.08,
            "duration": 5.0,
            "description": "Target takes 8% increased damage from all sources for 5s",
        }


@dataclass
class Conqueror:
    """Conqueror (Precision keystone).

    Dealing damage to champions grants stacks of adaptive force.
    At max stacks, melee champions heal from damage dealt.

    Stacking: melee 2 per hit, abilities 2 per cast (max 12).
    Duration: 5 seconds (refreshing).

    Usage:
        conq = Conqueror()
        bonus = conq.stat_bonus(champion_level=12, stacks=12, adaptive="ad")
        healing = conq.healing(post_mitigation_damage=200, is_melee=True)
    """
    name: str = "Conqueror"
    keystone_type: str = "Precision"
    max_stacks: int = 12

    def stat_bonus(self, champion_level: int, stacks: int, adaptive: str = "ad") -> Dict[str, Any]:
        """Calculate bonus AD or AP from Conqueror stacks.

        Args:
            champion_level: Current champion level
            stacks: Current number of stacks (0-12)
            adaptive: 'ad' for bonus AD, 'ap' for bonus AP

        Returns:
            Dict with bonus_AD or bonus_AP, stacks, is_fully_stacked
        """
        stacks = max(0, min(stacks, self.max_stacks))

        if adaptive == "ad":
            per_stack = _level_scale(1.08, 2.56, champion_level)
            return {
                "bonus_AD": round(per_stack * stacks, 2),
                "bonus_AP": 0.0,
                "per_stack_AD": per_stack,
                "stacks": stacks,
                "is_fully_stacked": stacks == self.max_stacks,
            }
        else:
            per_stack = _level_scale(1.8, 4.26, champion_level)
            return {
                "bonus_AD": 0.0,
                "bonus_AP": round(per_stack * stacks, 2),
                "per_stack_AP": per_stack,
                "stacks": stacks,
                "is_fully_stacked": stacks == self.max_stacks,
            }

    def healing(self, post_mitigation_damage: float, is_melee: bool = True) -> Dict[str, Any]:
        """Calculate healing at max stacks from damage dealt to champions.

        Only heals when fully stacked (12 stacks).

        Args:
            post_mitigation_damage: Damage dealt after mitigation
            is_melee: True for melee (8% heal), False for ranged (5%)

        Returns:
            Dict with heal amount
        """
        heal_pct = 0.08 if is_melee else 0.05
        heal = round(post_mitigation_damage * heal_pct, 2)
        return {
            "heal": heal,
            "heal_pct": f"{int(heal_pct * 100)}%",
            "requires_max_stacks": True,
        }


@dataclass
class HailOfBlades:
    """Hail of Blades (Domination keystone).

    Attacking a champion grants bonus attack speed for the next attacks.
    Can exceed the attack speed cap.

    Grants 2 stacks for 3 seconds, additional stack on attack timer reset.

    Usage:
        hob = HailOfBlades()
        bonus = hob.attack_speed_bonus(is_melee=True)
    """
    name: str = "Hail of Blades"
    keystone_type: str = "Domination"

    def attack_speed_bonus(self, is_melee: bool = True) -> Dict[str, Any]:
        """Calculate the bonus attack speed granted.

        Args:
            is_melee: True for melee (160%), False for ranged (80%)

        Returns:
            Dict with bonus_attack_speed, stacks, cooldown, duration
        """
        bonus = 160 if is_melee else 80
        return {
            "bonus_attack_speed": f"{bonus}%",
            "bonus_attack_speed_value": bonus,
            "initial_stacks": 2,
            "duration": 3.0,
            "cooldown": 10.0,
            "can_exceed_cap": True,
            "description": f"{bonus}% bonus attack speed for 3s (2 stacks + resets)",
        }


@dataclass
class GraspOfTheUndying:
    """Grasp of the Undying (Resolve keystone).

    In combat, generates stacks over time (1/sec, up to 4).
    Next basic attack on a champion deals bonus magic damage,
    heals, and grants permanent HP.

    Usage:
        grasp = GraspOfTheUndying()
        proc = grasp.proc_damage(champion_max_hp=2000, is_melee=True)
        heal = grasp.healing(champion_max_hp=2000, is_melee=True)
        perm = grasp.permanent_hp(is_melee=True)
    """
    name: str = "Grasp of the Undying"
    keystone_type: str = "Resolve"

    def proc_damage(self, champion_max_hp: float, is_melee: bool = True) -> Dict[str, Any]:
        """Calculate proc damage based on the user's max HP.

        Args:
            champion_max_hp: The attacking champion's maximum HP
            is_melee: True for melee (3.5%), False for ranged (1.4%)

        Returns:
            Dict with raw_damage, damage_type (always magic)
        """
        pct = 3.5 if is_melee else 1.4
        damage = round(champion_max_hp * pct / 100, 2)
        return {
            "raw_damage": damage,
            "damage_type": "magic",
            "hp_pct": f"{pct}%",
            "description": f"{pct}% max HP as magic damage",
        }

    def healing(self, champion_max_hp: float, is_melee: bool = True) -> Dict[str, Any]:
        """Calculate healing from proc.

        Args:
            champion_max_hp: The attacking champion's maximum HP
            is_melee: True for melee (1.3%), False for ranged (0.52%)

        Returns:
            Dict with heal amount
        """
        pct = 1.3 if is_melee else 0.52
        heal = round(champion_max_hp * pct / 100, 2)
        return {
            "heal": heal,
            "hp_pct": f"{pct}%",
        }

    def permanent_hp(self, is_melee: bool = True) -> Dict[str, Any]:
        """Permanent HP gained per proc.

        Args:
            is_melee: True for melee (+5 HP), False for ranged (+2 HP)

        Returns:
            Dict with permanent HP value
        """
        hp = 5 if is_melee else 2
        return {
            "permanent_hp": hp,
        }


# ─── MINOR RUNES (Precision Row 3 — Combat) ───


@dataclass
class LastStand:
    """Last Stand (Precision, row 3 minor rune).

    Deal 5% increased damage to champions while below 60% maximum health.
    Scales up to 11% increased damage while below 30% maximum health.
    Since patch 15.3, applies to true damage as well.

    Usage:
        ls = LastStand()
        amp = ls.damage_amp(missing_hp_pct=70)  # -> 0.11 (max)
    """
    name: str = "Last Stand"

    def damage_amp(self, missing_hp_pct: float) -> float:
        """Calculate damage amplification based on missing HP.

        Args:
            missing_hp_pct: Percentage of max HP that is missing (0–100).
                            60% current HP = 40% missing, 30% current HP = 70% missing.

        Returns:
            Damage amp as a decimal (0.05–0.11), or 0.0 if above 60% HP.
        """
        current_hp_pct = 100.0 - max(0.0, min(missing_hp_pct, 100.0))
        if current_hp_pct >= 60.0:
            return 0.0
        if current_hp_pct <= 30.0:
            return 0.11
        # Linear interpolation: 5% at 60% HP → 11% at 30% HP
        return round(0.05 + (60.0 - current_hp_pct) / 30.0 * 0.06, 4)


@dataclass
class CoupDeGrace:
    """Coup de Grace (Precision, row 3 minor rune).

    Deal 8% increased damage to champions below 40% maximum health.

    Usage:
        cdg = CoupDeGrace()
        amp = cdg.damage_amp(target_hp_pct=35)  # -> 0.08
    """
    name: str = "Coup de Grace"

    def damage_amp(self, target_hp_pct: float) -> float:
        """Calculate damage amp based on target current HP %.

        Args:
            target_hp_pct: Target's current HP as % of max (0–100).

        Returns:
            0.08 if target is below 40% HP, else 0.0.
        """
        return 0.08 if target_hp_pct < 40.0 else 0.0


@dataclass
class CutDown:
    """Cut Down (Precision, row 3 minor rune).

    Deal 5% to 15% increased damage to champions with more max HP than you.
    Scales linearly from 5% (target has 10% more max HP) to 15% (100% more).

    Usage:
        cd = CutDown()
        amp = cd.damage_amp(target_max_hp=3000, your_max_hp=2000)  # -> 0.1
    """
    name: str = "Cut Down"

    def damage_amp(self, target_max_hp: float, your_max_hp: float) -> float:
        """Calculate damage amp based on max HP difference.

        Args:
            target_max_hp: Target's maximum HP.
            your_max_hp: Your champion's maximum HP.

        Returns:
            Damage amp as decimal (0.05–0.15), or 0.0 if difference < 10%.
        """
        if your_max_hp <= 0:
            return 0.0
        diff_pct = (target_max_hp - your_max_hp) / your_max_hp * 100.0
        if diff_pct < 10.0:
            return 0.0
        if diff_pct >= 100.0:
            return 0.15
        return round(0.05 + (diff_pct - 10.0) / 90.0 * 0.10, 4)
