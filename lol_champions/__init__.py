"""League of Legends Champion Simulator Package."""

from .champion import Champion
from .ability import Ability
from .fiora import Fiora
from .target import Target
from .damage import calculate_damage, calculate_combo, effective_resistance, damage_after_mitigation
from .runes import PressTheAttack, Conqueror, HailOfBlades, GraspOfTheUndying
from .runes import LastStand, CoupDeGrace, CutDown
from .items import (
    SpearOfShojin,
    # On-hit
    BladeOfTheRuinedKing, WitsEnd, NashorsTooth, RecurveBow, Terminus, TitanicHydra,
    # Stacking on-hit
    KrakenSlayer,
    # Spellblade
    TrinityForce, IcebornGauntlet, LichBane,
    # Energized
    VoltaicCyclosword, RapidFirecannon, StatikkShiv, Stormrazor,
    # Amp
    LordDominiksRegards,
    # Active
    Stridebreaker, ProfaneHydra, RavenousHydra, HextechRocketbelt, Everfrost, HextechGunblade,
    # Burn / Immolate
    LiandrysTorment, SunfireAegis, HollowRadiance,
    # Conditional
    SunderedSky, DeadMansPlate,
    # Misc
    Tiamat, GuinsoosRageblade,
)
from .dps import optimize_dps
from .build_optimizer import optimize_build, ITEM_CATALOG, ITEM_ID_TO_PROC, validate_catalog
from .logger import log_result, log_build_results
from .live_client import is_game_active, get_active_player, get_player_list, get_game_stats
from .data_dragon import DataDragon

__all__ = [
    'Champion', 'Ability', 'Fiora',
    'Target',
    'calculate_damage', 'calculate_combo', 'effective_resistance', 'damage_after_mitigation',
    'PressTheAttack', 'Conqueror', 'HailOfBlades', 'GraspOfTheUndying',
    'LastStand', 'CoupDeGrace', 'CutDown',
    # Items
    'SpearOfShojin',
    'BladeOfTheRuinedKing', 'WitsEnd', 'NashorsTooth', 'RecurveBow', 'Terminus', 'TitanicHydra',
    'KrakenSlayer',
    'TrinityForce', 'IcebornGauntlet', 'LichBane',
    'VoltaicCyclosword', 'RapidFirecannon', 'StatikkShiv', 'Stormrazor',
    'LordDominiksRegards',
    'Stridebreaker', 'ProfaneHydra', 'RavenousHydra', 'HextechRocketbelt', 'Everfrost', 'HextechGunblade',
    'LiandrysTorment', 'SunfireAegis', 'HollowRadiance',
    'SunderedSky', 'DeadMansPlate',
    'Tiamat', 'GuinsoosRageblade',
    'optimize_dps',
    'optimize_build', 'ITEM_CATALOG', 'ITEM_ID_TO_PROC', 'validate_catalog',
    'log_result', 'log_build_results',
    'is_game_active', 'get_active_player', 'get_player_list', 'get_game_stats',
    'DataDragon',
]
__version__ = '1.6.0'
