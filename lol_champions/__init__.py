"""League of Legends Champion Simulator Package."""

from .champion import Champion
from .ability import Ability
from .fiora import Fiora
from .target import Target
from .damage import calculate_damage, calculate_combo, effective_resistance, damage_after_mitigation
from .runes import PressTheAttack, Conqueror, HailOfBlades, GraspOfTheUndying

__all__ = [
    'Champion', 'Ability', 'Fiora',
    'Target',
    'calculate_damage', 'calculate_combo', 'effective_resistance', 'damage_after_mitigation',
    'PressTheAttack', 'Conqueror', 'HailOfBlades', 'GraspOfTheUndying',
]
__version__ = '1.1.0'
