"""Target class for damage calculation."""

from dataclasses import dataclass


@dataclass
class Target:
    """Represents a damage target with defensive stats.

    Attributes:
        max_hp: Target's maximum health points
        armor: Total armor
        mr: Total magic resistance
    """
    max_hp: float = 1000.0
    armor: float = 0.0
    mr: float = 0.0

    @classmethod
    def from_champion(cls, champion) -> 'Target':
        """Create a Target from any Champion instance."""
        return cls(
            max_hp=champion.total_HP,
            armor=champion.total_AR,
            mr=champion.total_MR,
        )

    def __str__(self) -> str:
        return f"Target(HP: {self.max_hp}, Armor: {self.armor}, MR: {self.mr})"
