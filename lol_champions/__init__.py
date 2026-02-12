"""League of Legends Champion Simulator Package."""

from .champion import Champion
from .ability import Ability
from .fiora import Fiora
from .target import Target
from .damage import calculate_damage, calculate_combo, effective_resistance, damage_after_mitigation
from .runes import PressTheAttack, Conqueror, HailOfBlades, GraspOfTheUndying
from .runes import LastStand, CoupDeGrace, CutDown
from .items import SpearOfShojin
from .dps import optimize_dps
from .live_client import is_game_active, get_active_player, get_player_list, get_game_stats
from .data_dragon import DataDragon

__all__ = [
    'Champion', 'Ability', 'Fiora',
    'Target',
    'calculate_damage', 'calculate_combo', 'effective_resistance', 'damage_after_mitigation',
    'PressTheAttack', 'Conqueror', 'HailOfBlades', 'GraspOfTheUndying',
    'LastStand', 'CoupDeGrace', 'CutDown',
    'SpearOfShojin',
    'optimize_dps',
    'is_game_active', 'get_active_player', 'get_player_list', 'get_game_stats',
    'DataDragon',
]
__version__ = '1.4.0'
