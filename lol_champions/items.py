"""Item passive and active effects for League of Legends damage calculations.

Models item passives/actives that deal damage or amplify damage.
Proc items expose a ``proc_damage(champion, target)`` method returning
a dict with ``raw_damage`` and ``damage_type`` keys — the same contract
used by abilities and runes, so the result feeds directly into
``calculate_damage()``.

Stat-only items (no proc) use ``DataDragon.item_stats()`` +
``champion.add_stats()`` — no dataclass needed.

All values sourced from https://leagueoflegends.fandom.com/wiki/
"""

from dataclasses import dataclass
from typing import Dict, Any


def _level_scale(min_val: float, max_val: float, level: int,
                 max_level: int = 18) -> float:
    """Linear interpolation for level-based item scaling (1-18)."""
    lvl = min(max(level, 1), max_level)
    return min_val + (max_val - min_val) * (lvl - 1) / (max_level - 1)


# ─── Action sets ───

# Actions that apply on-hit effects (life steal, BotRK, Wit's End, etc.)
ON_HIT_ACTIONS = {"AA", "Q", "E_FIRST", "E_CRIT"}

# Actions that count as ability casts (arm Spellblade, trigger Liandry's)
ABILITY_CAST_ACTIONS = {"Q", "W", "E_ACTIVATE", "R_ACTIVATE"}

# Ability damage actions (trigger Liandry's burn — NOT basic AAs)
ABILITY_DAMAGE_ACTIONS = {"Q", "W", "E_FIRST", "E_CRIT"}

# ─── Shojin-specific action sets (kept for backward compat) ───
SHOJIN_AMPLIFIED_ACTIONS = {"Q", "W", "E", "E_FIRST", "E_CRIT", "PASSIVE"}
SHOJIN_STACK_GRANTING_ACTIONS = {"Q", "W", "E", "E_FIRST", "E_CRIT"}


# ═══════════════════════════════════════════════════════════════════════
# STACKING AMPLIFIER
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class SpearOfShojin:
    """Spear of Shojin — Focused Will passive.

    Stats: +45 AD, +450 HP, 25 basic ability haste.

    Passive — Focused Will:
        Dealing ability damage grants a stack for 6s (max 4).
        Each stack: +3% ability/proc damage (up to 12%).

    Interactions:
        - Amplifies ALL damage types including true damage.
        - Does NOT amplify basic auto-attacks.
        - Does NOT grant stacks from champion passive damage.
        - Triggering ability does NOT benefit from its own stack.
        - Fiora E empowered attacks grant stacks and benefit.
    """
    name: str = "Spear of Shojin"
    stacks: int = 0
    max_stacks: int = 4
    amp_per_stack: float = 0.03

    def damage_amp(self) -> float:
        return min(self.stacks, self.max_stacks) * self.amp_per_stack

    def add_stack(self) -> int:
        self.stacks = min(self.stacks + 1, self.max_stacks)
        return self.stacks

    def reset(self) -> None:
        self.stacks = 0

    @staticmethod
    def is_amplified(action: str) -> bool:
        return action.upper() in SHOJIN_AMPLIFIED_ACTIONS

    @staticmethod
    def grants_stack(action: str) -> bool:
        return action.upper() in SHOJIN_STACK_GRANTING_ACTIONS

    def modifier_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "amp": self.damage_amp()}


# ═══════════════════════════════════════════════════════════════════════
# ON-HIT ITEMS — proc every basic attack / on-hit ability
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class BladeOfTheRuinedKing:
    """Blade of the Ruined King — Mist's Edge.

    Stats: +40 AD, +25% AS.
    On-hit: 9% (melee) / 6% (ranged) of target's current HP as physical.
    Capped at 100 vs minions/monsters.
    """
    name: str = "Blade of the Ruined King"
    melee_pct: float = 0.09
    ranged_pct: float = 0.06

    def proc_damage(self, champion, target, **ctx) -> dict:
        pct = self.melee_pct if getattr(champion, 'is_melee', True) else self.ranged_pct
        hp = ctx.get("target_current_hp", target.max_hp)
        return {"raw_damage": hp * pct, "damage_type": "physical"}


@dataclass
class WitsEnd:
    """Wit's End — Fray.

    Stats: +40 AD, +40% AS, +40 MR.
    On-hit: 45 bonus magic damage.
    """
    name: str = "Wit's End"
    flat_magic: float = 45.0

    def proc_damage(self, champion, target, **ctx) -> dict:
        return {"raw_damage": self.flat_magic, "damage_type": "magic"}


@dataclass
class NashorsTooth:
    """Nashor's Tooth — Icathian Bite.

    Stats: +100 AP, +50% AS.
    On-hit: 15 + 15% AP magic damage.
    """
    name: str = "Nashor's Tooth"
    base_damage: float = 15.0
    ap_ratio: float = 0.15

    def proc_damage(self, champion, target, **ctx) -> dict:
        ap = getattr(champion, 'total_AP', 0)
        return {"raw_damage": self.base_damage + ap * self.ap_ratio,
                "damage_type": "magic"}


@dataclass
class RecurveBow:
    """Recurve Bow — Sting.

    Stats: +15% AS.
    On-hit: 15 physical damage.
    """
    name: str = "Recurve Bow"
    flat_physical: float = 15.0

    def proc_damage(self, champion, target, **ctx) -> dict:
        return {"raw_damage": self.flat_physical, "damage_type": "physical"}


@dataclass
class Terminus:
    """Terminus — Shadow / Juxtaposition.

    Stats: +30 AD, +30% AS.
    On-hit: 30 magic damage.
    Juxtaposition: alternating Light/Dark hits grant
      Light: +6-8 AR/MR per stack (max 3)
      Dark: +10% armor/magic pen per stack (max 3)
    (Juxtaposition stacking tracked in DPS optimizer.)
    """
    name: str = "Terminus"
    flat_magic: float = 30.0

    def proc_damage(self, champion, target, **ctx) -> dict:
        return {"raw_damage": self.flat_magic, "damage_type": "magic"}


@dataclass
class TitanicHydra:
    """Titanic Hydra — Colossus (passive on-hit) + Titanic Crescent (active).

    Stats: +50 AD, +500 HP.
    Passive on-hit (primary target): 5 + 1% (melee) / 0.5% (ranged) your max HP physical.
    Active — Titanic Crescent: AA reset, primary target takes 4% (melee) / 2% (ranged) max HP.
      10s cooldown.
    """
    name: str = "Titanic Hydra"
    passive_flat: float = 5.0
    melee_passive_pct: float = 0.01
    ranged_passive_pct: float = 0.005
    melee_active_pct: float = 0.04
    ranged_active_pct: float = 0.02
    active_cooldown: float = 10.0

    def proc_damage(self, champion, target, **ctx) -> dict:
        """Passive on-hit damage to primary target."""
        pct = self.melee_passive_pct if getattr(champion, 'is_melee', True) else self.ranged_passive_pct
        hp = getattr(champion, 'total_HP', 0)
        return {"raw_damage": self.passive_flat + hp * pct, "damage_type": "physical"}

    def active_damage(self, champion, target, **ctx) -> dict:
        """Titanic Crescent active — enhanced AA to primary target."""
        pct = self.melee_active_pct if getattr(champion, 'is_melee', True) else self.ranged_active_pct
        hp = getattr(champion, 'total_HP', 0)
        return {"raw_damage": hp * pct, "damage_type": "physical"}

    @staticmethod
    def is_active() -> bool:
        return True


# ═══════════════════════════════════════════════════════════════════════
# STACKING ON-HIT — proc every Nth hit
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class KrakenSlayer:
    """Kraken Slayer — Bring It Down.

    Stats: +40 AD, +25% AS.
    Every 3rd hit: 150-210 (lv1-18, melee) / 120-168 (ranged) bonus physical.
    Bonus missing HP scaling: 0-75% based on target missing HP.
    """
    name: str = "Kraken Slayer"
    melee_min: float = 150.0
    melee_max: float = 210.0
    ranged_min: float = 120.0
    ranged_max: float = 168.0

    def proc_damage(self, champion, target, **ctx) -> dict:
        is_melee = getattr(champion, 'is_melee', True)
        lo = self.melee_min if is_melee else self.ranged_min
        hi = self.melee_max if is_melee else self.ranged_max
        base = _level_scale(lo, hi, champion.level)
        return {"raw_damage": base, "damage_type": "physical"}

    @staticmethod
    def hits_to_proc() -> int:
        return 3


# ═══════════════════════════════════════════════════════════════════════
# SPELLBLADE ITEMS — unique passive, only one active at a time
# Next on-hit after ability cast within 10s. 1.5s internal CD.
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class TrinityForce:
    """Trinity Force — Spellblade.

    Stats: +35 AD, +300 HP, +33% AS, 15 ability haste.
    Spellblade: After ability cast, next auto deals 200% base AD bonus physical.
    1.5s internal cooldown.
    """
    name: str = "Trinity Force"
    base_ad_ratio: float = 2.0
    cooldown: float = 1.5

    def proc_damage(self, champion, target, **ctx) -> dict:
        return {"raw_damage": champion.base_AD * self.base_ad_ratio,
                "damage_type": "physical"}

    @staticmethod
    def is_spellblade() -> bool:
        return True


@dataclass
class IcebornGauntlet:
    """Iceborn Gauntlet — Spellblade.

    Stats: +300 HP, +50 AR, 15 ability haste.
    Spellblade: After ability cast, next auto deals 150% base AD bonus physical.
    Creates frost field slowing 25% (melee) / 12.5% (ranged) for 2s.
    1.5s internal cooldown.
    """
    name: str = "Iceborn Gauntlet"
    base_ad_ratio: float = 1.5
    cooldown: float = 1.5

    def proc_damage(self, champion, target, **ctx) -> dict:
        return {"raw_damage": champion.base_AD * self.base_ad_ratio,
                "damage_type": "physical"}

    @staticmethod
    def is_spellblade() -> bool:
        return True


@dataclass
class LichBane:
    """Lich Bane — Spellblade.

    Stats: +85 AP, +8% MS.
    Spellblade: After ability cast, next auto deals 75% base AD + 40% AP magic.
    +50% bonus AS while buff active. 1.5s internal cooldown.
    """
    name: str = "Lich Bane"
    base_ad_ratio: float = 0.75
    ap_ratio: float = 0.40
    cooldown: float = 1.5

    def proc_damage(self, champion, target, **ctx) -> dict:
        ap = getattr(champion, 'total_AP', 0)
        return {"raw_damage": champion.base_AD * self.base_ad_ratio + ap * self.ap_ratio,
                "damage_type": "magic"}

    @staticmethod
    def is_spellblade() -> bool:
        return True


# ═══════════════════════════════════════════════════════════════════════
# ENERGIZED ITEMS — proc after accumulating 100 energy stacks
# 6 stacks per AA, ~1 per 24 units moved. All share the same pool.
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class VoltaicCyclosword:
    """Voltaic Cyclosword — Firmament.

    Stats: +55 AD, +15% AS.
    Energized: 100 physical damage + 99% slow (melee) / 20% slow (ranged) for 0.75s.
    """
    name: str = "Voltaic Cyclosword"
    flat_damage: float = 100.0
    stacks_per_aa: int = 6
    max_stacks: int = 100

    def proc_damage(self, champion, target, **ctx) -> dict:
        return {"raw_damage": self.flat_damage, "damage_type": "physical"}

    @staticmethod
    def is_energized() -> bool:
        return True


@dataclass
class RapidFirecannon:
    """Rapid Firecannon — Sharpshooter.

    Stats: +25% AS.
    Energized: 40 magic damage + 35% bonus range (max +150 units).
    """
    name: str = "Rapid Firecannon"
    flat_damage: float = 40.0
    stacks_per_aa: int = 6
    max_stacks: int = 100

    def proc_damage(self, champion, target, **ctx) -> dict:
        return {"raw_damage": self.flat_damage, "damage_type": "magic"}

    @staticmethod
    def is_energized() -> bool:
        return True


@dataclass
class StatikkShiv:
    """Statikk Shiv — Electrospark.

    Stats: +45% AS.
    Energized: Empowers next 3 AAs to chain-lightning for 60 magic vs champs
    (85 vs non-champs), up to 5 bounces. Single-target value used here.
    """
    name: str = "Statikk Shiv"
    champ_damage: float = 60.0
    stacks_per_aa: int = 6
    max_stacks: int = 100

    def proc_damage(self, champion, target, **ctx) -> dict:
        return {"raw_damage": self.champ_damage, "damage_type": "magic"}

    @staticmethod
    def is_energized() -> bool:
        return True


@dataclass
class Stormrazor:
    """Stormrazor — Bolt.

    Stats: +45 AD.
    Energized: 100 magic damage + 45% bonus MS for 1.5s.
    """
    name: str = "Stormrazor"
    flat_damage: float = 100.0
    stacks_per_aa: int = 6
    max_stacks: int = 100

    def proc_damage(self, champion, target, **ctx) -> dict:
        return {"raw_damage": self.flat_damage, "damage_type": "magic"}

    @staticmethod
    def is_energized() -> bool:
        return True


# ═══════════════════════════════════════════════════════════════════════
# DAMAGE AMPLIFIER ITEMS — fit into damage_modifiers pattern
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class LordDominiksRegards:
    """Lord Dominik's Regards — Giant Slayer.

    Stats: +35 AD, +30% armor pen.
    Passive: 0-15% increased damage vs champions based on bonus HP difference.
    Linear from 10% to 100% bonus HP diff → 0% to 15% amp.
    """
    name: str = "Lord Dominik's Regards"

    def damage_amp(self, target_max_hp: float, your_max_hp: float) -> float:
        diff = max(target_max_hp - your_max_hp, 0)
        ratio = min(diff / your_max_hp, 1.0) if your_max_hp > 0 else 0
        return round(ratio * 0.15, 4)

    def modifier_dict(self, target_max_hp: float, your_max_hp: float) -> dict:
        return {"name": self.name, "amp": self.damage_amp(target_max_hp, your_max_hp)}


# ═══════════════════════════════════════════════════════════════════════
# ACTIVE ITEMS — manual activation, modeled as DPS actions
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class Stridebreaker:
    """Stridebreaker — Breaking Shockwave.

    Stats: +45 AD, +300 HP, +20% AS.
    Active: 80% total AD physical in 450 radius. 35% slow 3s.
    15s cooldown (not reduced by AH). Castable while moving.
    """
    name: str = "Stridebreaker"
    ad_ratio: float = 0.80
    cooldown: float = 15.0

    def proc_damage(self, champion, target, **ctx) -> dict:
        return {"raw_damage": champion.total_AD * self.ad_ratio,
                "damage_type": "physical"}

    @staticmethod
    def is_active() -> bool:
        return True


@dataclass
class ProfaneHydra:
    """Profane Hydra — Heretical Cleave (active) + Cleave (passive).

    Stats: +60 AD, 15 ability haste, 18 lethality.
    Passive Cleave: 40% (melee) / 20% (ranged) AD AoE around target (no primary).
    Active: 80% AD physical in 450 radius (hits primary in 1v1). 10s CD.
    """
    name: str = "Profane Hydra"
    active_ad_ratio: float = 0.80
    cooldown: float = 10.0

    def proc_damage(self, champion, target, **ctx) -> dict:
        """Active damage (hits primary target in 1v1)."""
        return {"raw_damage": champion.total_AD * self.active_ad_ratio,
                "damage_type": "physical"}

    @staticmethod
    def is_active() -> bool:
        return True


@dataclass
class RavenousHydra:
    """Ravenous Hydra — Ravenous Crescent (active) + Cleave (passive).

    Stats: +65 AD, 25 ability haste, 10% life steal.
    Passive Cleave: 40% (melee) / 20% (ranged) AD AoE (no primary target damage).
    Active: 80% AD physical in 450 radius cone (hits primary in 1v1). 10s CD.
    """
    name: str = "Ravenous Hydra"
    active_ad_ratio: float = 0.80
    cooldown: float = 10.0

    def proc_damage(self, champion, target, **ctx) -> dict:
        """Active damage (hits primary target in 1v1)."""
        return {"raw_damage": champion.total_AD * self.active_ad_ratio,
                "damage_type": "physical"}

    @staticmethod
    def is_active() -> bool:
        return True


@dataclass
class HextechRocketbelt:
    """Hextech Rocketbelt — Supersonic.

    Stats: +80 AP, +300 HP, 15 ability haste.
    Active: 275-unit dash + 100 + 10% AP magic damage. AA reset. 40s CD.
    """
    name: str = "Hextech Rocketbelt"
    base_damage: float = 100.0
    ap_ratio: float = 0.10
    cooldown: float = 40.0

    def proc_damage(self, champion, target, **ctx) -> dict:
        ap = getattr(champion, 'total_AP', 0)
        return {"raw_damage": self.base_damage + ap * self.ap_ratio,
                "damage_type": "magic"}

    @staticmethod
    def is_active() -> bool:
        return True


@dataclass
class Everfrost:
    """Everfrost — Glaciate.

    Stats: +70 AP, +300 HP, +600 mana, 25 ability haste.
    Active: 300 + 85% AP magic damage cone. Root 1.5s (center) / slow (outer). 30s CD.
    """
    name: str = "Everfrost"
    base_damage: float = 300.0
    ap_ratio: float = 0.85
    cooldown: float = 30.0

    def proc_damage(self, champion, target, **ctx) -> dict:
        ap = getattr(champion, 'total_AP', 0)
        return {"raw_damage": self.base_damage + ap * self.ap_ratio,
                "damage_type": "magic"}

    @staticmethod
    def is_active() -> bool:
        return True


# ═══════════════════════════════════════════════════════════════════════
# BURN / DOT ITEMS
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class LiandrysTorment:
    """Liandry's Torment — Torment.

    Stats: +80 AP, +300 HP.
    On ability damage: 1% target max HP magic per 0.5s for 3s (6% total).
    Suffering: +2%/s in combat (up to +6%), multiplicative with other amps.
    Modeled here as flat 6% max HP burn per ability hit (excluding Suffering ramp).
    """
    name: str = "Liandry's Torment"
    total_burn_pct: float = 0.06

    def burn_damage(self, target, **ctx) -> dict:
        """Total burn damage per ability hit (3s duration)."""
        return {"raw_damage": target.max_hp * self.total_burn_pct,
                "damage_type": "magic"}

    @staticmethod
    def is_burn() -> bool:
        return True


@dataclass
class SunfireAegis:
    """Sunfire Aegis — Immolate.

    Stats: +50 AR, +500 HP.
    Aura: 20 + 1% bonus HP magic damage/s to nearby enemies.
    Always active in melee range during combat.
    """
    name: str = "Sunfire Aegis"
    base_dps: float = 20.0
    bonus_hp_ratio: float = 0.01

    def dps(self, champion, **ctx) -> float:
        """Magic DPS in combat (always-on aura)."""
        bonus_hp = getattr(champion, 'bonus_HP', 0)
        return self.base_dps + bonus_hp * self.bonus_hp_ratio

    @staticmethod
    def is_immolate() -> bool:
        return True


@dataclass
class HollowRadiance:
    """Hollow Radiance — Immolate.

    Stats: +50 MR, +500 HP, 10 ability haste.
    Aura: 15 + 1% bonus HP magic damage/s to nearby enemies.
    """
    name: str = "Hollow Radiance"
    base_dps: float = 15.0
    bonus_hp_ratio: float = 0.01

    def dps(self, champion, **ctx) -> float:
        bonus_hp = getattr(champion, 'bonus_HP', 0)
        return self.base_dps + bonus_hp * self.bonus_hp_ratio

    @staticmethod
    def is_immolate() -> bool:
        return True


# ═══════════════════════════════════════════════════════════════════════
# CONDITIONAL ITEMS — proc under specific conditions
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class SunderedSky:
    """Sundered Sky — Lightshield Strike.

    Stats: +50 AD, +300 HP.
    First AA vs a champion: guaranteed crit (60% bonus crit damage).
    Heals for 100% (melee) / 50% (ranged) base AD + 6% missing HP.
    10s CD per target.
    """
    name: str = "Sundered Sky"
    crit_bonus_pct: float = 0.60
    melee_heal_ad_ratio: float = 1.0
    ranged_heal_ad_ratio: float = 0.5
    missing_hp_heal_pct: float = 0.06
    cooldown: float = 10.0

    def proc_damage(self, champion, target, **ctx) -> dict:
        """Bonus crit damage on first hit (60% of total AD extra)."""
        return {"raw_damage": champion.total_AD * self.crit_bonus_pct,
                "damage_type": "physical"}

    def proc_heal(self, champion, current_hp: float = 0, max_hp: float = 0) -> float:
        """Heal on proc: base AD + 6% missing HP."""
        is_melee = getattr(champion, 'is_melee', True)
        ratio = self.melee_heal_ad_ratio if is_melee else self.ranged_heal_ad_ratio
        missing = max(max_hp - current_hp, 0)
        return champion.base_AD * ratio + missing * self.missing_hp_heal_pct

    @staticmethod
    def is_conditional() -> bool:
        return True


@dataclass
class DeadMansPlate:
    """Dead Man's Plate — Shipwrecker.

    Stats: +300 HP, +45 AR.
    At 100 momentum: 40 + 120% base AD bonus physical on next basic attack.
    Momentum: 7 stacks per 0.25s while moving (max 100).
    Consumed on basic attack.
    """
    name: str = "Dead Man's Plate"
    flat_damage: float = 40.0
    base_ad_ratio: float = 1.20

    def proc_damage(self, champion, target, **ctx) -> dict:
        """Full-momentum proc damage."""
        return {"raw_damage": self.flat_damage + champion.base_AD * self.base_ad_ratio,
                "damage_type": "physical"}

    @staticmethod
    def is_conditional() -> bool:
        return True


# ═══════════════════════════════════════════════════════════════════════
# MISC ITEMS WITH DAMAGE EFFECTS
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class Tiamat:
    """Tiamat — Cleave.

    Stats: +25 AD.
    Passive Cleave: 40% (melee) / 20% (ranged) AD AoE around target.
    No damage to primary target in 1v1. No active.
    Included for completeness — no proc_damage since primary target
    doesn't take Cleave damage.
    """
    name: str = "Tiamat"


@dataclass
class GuinsoosRageblade:
    """Guinsoo's Rageblade — Seething Strike / Phantom Hit.

    Stats: +30% AS.
    Stacking: 4 stacks of 8% bonus AS each (lasts 3s per stack, max 32%).
    Phantom Hit: Every 2 phantom stacks, next auto triggers a phantom hit
    that re-applies on-hit effects with 0.15s delay.
    Takes 6 total attacks to trigger first phantom hit.
    No direct damage — duplicates on-hit effects.
    """
    name: str = "Guinsoo's Rageblade"
    as_per_stack: float = 8.0
    max_stacks: int = 4
    phantom_interval: int = 2

    @staticmethod
    def is_phantom_hit() -> bool:
        return True


@dataclass
class HextechGunblade:
    """Hextech Gunblade — Lightning Bolt.

    Stats: +40 AD, +60 AP.
    Active: 175-253 (lv1-18) + 30% AP magic damage, 40% slow 2s. 40s CD.
    """
    name: str = "Hextech Gunblade"
    min_damage: float = 175.0
    max_damage: float = 253.0
    ap_ratio: float = 0.30
    cooldown: float = 40.0

    def proc_damage(self, champion, target, **ctx) -> dict:
        base = _level_scale(self.min_damage, self.max_damage, champion.level)
        ap = getattr(champion, 'total_AP', 0)
        return {"raw_damage": base + ap * self.ap_ratio, "damage_type": "magic"}

    @staticmethod
    def is_active() -> bool:
        return True
