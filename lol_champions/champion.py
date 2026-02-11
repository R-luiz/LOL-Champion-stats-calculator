"""Base Champion class for League of Legends champions."""

from dataclasses import dataclass, field


@dataclass
class Champion:
    """Base class for all League of Legends champions.
    
    Attributes:
        base_AD: Base attack damage
        AD_scaling: Attack damage per level
        base_AP: Base ability power (magic damage)
        AP_scaling: Ability power per level
        base_HP: Base health points
        HP_scaling: Health points per level
        base_AR: Base armor
        AR_scaling: Armor per level
        base_MR: Base magic resist
        MR_scaling: Magic resist per level
        bonus_AD: Bonus attack damage from items
        bonus_AP: Bonus ability power from items
        bonus_HP: Bonus health from items
        bonus_AR: Bonus armor from items
        bonus_MR: Bonus magic resist from items
        level: Current champion level
        max_level: Maximum champion level
        skill_points: Available points to level up abilities
    """
    
    base_AD: float
    AD_scaling: float
    base_AP: float
    AP_scaling: float
    base_HP: float
    HP_scaling: float
    base_AR: float
    AR_scaling: float
    base_MR: float
    MR_scaling: float
    bonus_AD: float = 0.0
    bonus_AP: float = 0.0
    bonus_HP: float = 0.0
    bonus_AR: float = 0.0
    bonus_MR: float = 0.0
    # Penetration stats (from items/runes)
    lethality: float = 0.0
    armor_pen_pct: float = 0.0
    magic_pen_flat: float = 0.0
    magic_pen_pct: float = 0.0
    # Champion type
    is_melee: bool = True
    level: int = 1
    max_level: int = 20
    skill_points: int = 0
    total_AD: float = field(init=False)
    total_AP: float = field(init=False)
    total_HP: float = field(init=False)
    total_AR: float = field(init=False)
    total_MR: float = field(init=False)

    def __post_init__(self):
        """Calculate total stats after initialization."""
        self.total_AD = self.base_AD + self.bonus_AD
        self.total_AP = self.base_AP + self.bonus_AP
        self.total_HP = self.base_HP + self.bonus_HP
        self.total_AR = self.base_AR + self.bonus_AR
        self.total_MR = self.base_MR + self.bonus_MR

    @staticmethod
    def scaling_value(new_level: int, value: float) -> float:
        """Calculate stat scaling value for a given level.
        
        Args:
            new_level: The level to calculate scaling for
            value: The base scaling value
            
        Returns:
            Scaled value rounded to 2 decimal places
        """
        return round(value * (0.65 + 0.035 * new_level), 2)
    
    def __str__(self) -> str:
        """String representation of champion stats."""
        return (f"Champion Level: {self.level} (SP: {self.skill_points}) Stats:\n"
                f"AD: {round(self.base_AD, 2)} AP: {round(self.base_AP, 2)} "
                f"HP: {round(self.base_HP, 2)} AR: {round(self.base_AR, 2)} MR: {round(self.base_MR, 2)}")
    
    def level_up(self):
        """Increase champion level and apply stat scaling.
        
        Grants 1 skill point per level that can be used to level up abilities.
        """
        if self.level < self.max_level:
            self.level += 1
            self.skill_points += 1
            self.base_AD += self.scaling_value(self.level, self.AD_scaling)
            self.base_AP += self.scaling_value(self.level, self.AP_scaling)
            self.base_HP += self.scaling_value(self.level, self.HP_scaling)
            self.base_AR += self.scaling_value(self.level, self.AR_scaling)
            self.base_MR += self.scaling_value(self.level, self.MR_scaling)
            self.total_AD = self.base_AD + self.bonus_AD
            self.total_AP = self.base_AP + self.bonus_AP
            self.total_HP = self.base_HP + self.bonus_HP
            self.total_AR = self.base_AR + self.bonus_AR
            self.total_MR = self.base_MR + self.bonus_MR
            print(f"Level up! Now level {self.level}. Skill points: {self.skill_points}")
        else:
            print("Champion is already at max level.")
    
    def add_stats(self, bonus_AD: float = 0.0, bonus_AP: float = 0.0,
                  bonus_HP: float = 0.0, bonus_AR: float = 0.0, bonus_MR: float = 0.0,
                  lethality: float = 0.0, armor_pen_pct: float = 0.0,
                  magic_pen_flat: float = 0.0, magic_pen_pct: float = 0.0):
        """Add bonus stats from items or buffs.

        Args:
            bonus_AD: Additional attack damage
            bonus_AP: Additional ability power
            bonus_HP: Additional health points
            bonus_AR: Additional armor
            bonus_MR: Additional magic resist
            lethality: Flat armor penetration
            armor_pen_pct: Percentage armor penetration (decimal, e.g. 0.35)
            magic_pen_flat: Flat magic penetration
            magic_pen_pct: Percentage magic penetration (decimal, e.g. 0.40)
        """
        self.bonus_AD += bonus_AD
        self.bonus_AP += bonus_AP
        self.bonus_HP += bonus_HP
        self.bonus_AR += bonus_AR
        self.bonus_MR += bonus_MR
        self.lethality += lethality
        self.armor_pen_pct += armor_pen_pct
        self.magic_pen_flat += magic_pen_flat
        self.magic_pen_pct += magic_pen_pct
        self.total_AD = self.base_AD + self.bonus_AD
        self.total_AP = self.base_AP + self.bonus_AP
        self.total_HP = self.base_HP + self.bonus_HP
        self.total_AR = self.base_AR + self.bonus_AR
        self.total_MR = self.base_MR + self.bonus_MR
