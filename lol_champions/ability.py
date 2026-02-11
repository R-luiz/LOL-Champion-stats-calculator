"""Ability class for champion abilities."""

from dataclasses import dataclass


@dataclass
class Ability:
    """Represents a champion's ability.
    
    Attributes:
        name: The name of the ability
        max_level: Maximum level for the ability (5 for Q/W/E, 3 for R)
        current_level: Current level of the ability
    """
    
    name: str
    max_level: int = 5
    current_level: int = 0
    
    def level_up(self) -> bool:
        """Increase ability level by 1.
        
        Returns:
            True if level up was successful, False if already at max level
        """
        if self.current_level < self.max_level:
            self.current_level += 1
            return True
        return False
    
    def __str__(self) -> str:
        """String representation of the ability."""
        return f"{self.name} [Level {self.current_level}/{self.max_level}]"
