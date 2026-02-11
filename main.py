from dataclasses import dataclass, field
from typing import List

@dataclass
class Champion:
    base_AD: float
    AD_scaling: float
    base_HP: float
    HP_scaling: float
    base_AR: float
    AR_scaling: float
    base_MR: float
    MR_scaling: float
    bonus_AD: float = 0.0
    bonus_HP: float = 0.0
    bonus_AR: float = 0.0
    bonus_MR: float = 0.0
    level: int = 1
    max_level: int = 20
    total_AD: float = field(init=False)
    total_HP: float = field(init=False)
    total_AR: float = field(init=False)
    total_MR: float = field(init=False)

    
    def __post_init__(self):
        """Called after __init__ to perform additional initialization."""
        self.total_AD = self.base_AD + self.bonus_AD
        self.total_HP = self.base_HP + self.bonus_HP
        self.total_AR = self.base_AR + self.bonus_AR
        self.total_MR = self.base_MR + self.bonus_MR

    @staticmethod
    def scaling_value(new_level: int, value: float):
        return round(value*(0.65+0.035*new_level),2)
    
    def __str__(self):
        return f"Champion Level: {self.level} Stats:\nAD: {round(self.base_AD, 2)} HP: {round(self.base_HP, 2)} AR: {round(self.base_AR, 2)} MR: {round(self.base_MR, 2)}"
    
    def level_up(self):
        if self.level < self.max_level:
            self.level += 1
            self.base_AD += self.scaling_value(self.level, self.AD_scaling)
            self.base_HP += self.scaling_value(self.level, self.HP_scaling)
            self.base_AR += self.scaling_value(self.level, self.AR_scaling)
            self.base_MR += self.scaling_value(self.level, self.MR_scaling)
            self.total_AD = self.base_AD + self.bonus_AD
            self.total_HP = self.base_HP + self.bonus_HP
            self.total_AR = self.base_AR + self.bonus_AR
            self.total_MR = self.base_MR + self.bonus_MR
        else:
            print("Champion is already at max level.")
    
    def add_stats(self, bonus_AD: float = 0.0, bonus_HP: float = 0.0, bonus_AR: float = 0.0, bonus_MR: float = 0.0):
        self.bonus_AD += bonus_AD
        self.bonus_HP += bonus_HP
        self.bonus_AR += bonus_AR
        self.bonus_MR += bonus_MR
        self.total_AD = self.base_AD + self.bonus_AD
        self.total_HP = self.base_HP + self.bonus_HP
        self.total_AR = self.base_AR + self.bonus_AR
        self.total_MR = self.base_MR + self.bonus_MR

@dataclass
class Ability:
    name: str
    max_level: int = 5
    current_level: int = 0
    
    def level_up(self):
        if self.current_level < self.max_level:
            self.current_level += 1
            return True
        return False

class Fiora(Champion):
    def __init__(self):
        super().__init__(base_AD=66, AD_scaling=3.3, base_HP=620, HP_scaling=99, base_AR=33, AR_scaling=4.7, base_MR=32, MR_scaling=2.05)
        self.Q_ability = Ability("Lunge", max_level=5)
        self.W_ability = Ability("Riposte", max_level=5)
        self.E_ability = Ability("Bladework", max_level=5)
        self.R_ability = Ability("Grand Challenge", max_level=3)
    
    def level_ability(self, ability: str):
        """Level up a specific ability (Q, W, E, or R)."""
        if ability == 'Q':
            return self.Q_ability.level_up()
        elif ability == 'W':
            return self.W_ability.level_up()
        elif ability == 'E':
            return self.E_ability.level_up()
        elif ability == 'R':
            return self.R_ability.level_up()
        return False
    
    def passive(self, target_max_hp: float):
        """Duelist's Dance - Hitting a vital deals true damage, heals, and grants movement speed.
        
        Args:
            target_max_hp: The maximum HP of the target whose vital is being hit
            
        Returns:
            Dictionary containing true damage, heal amount, and movement speed bonus
        """
        # True damage: 3% (+ 4% per 100 bonus AD) of target's maximum health
        base_percent = 3.0
        bonus_ad_scaling = (self.bonus_AD / 100) * 4.0
        true_damage_percent = base_percent + bonus_ad_scaling
        true_damage = (target_max_hp * true_damage_percent) / 100
        
        # Heal: 35 – 107.65 (based on level)
        # Linear interpolation from level 1 (35) to level 18 (107.65)
        heal_base = 35
        heal_max = 107.65
        heal_per_level = (heal_max - heal_base) / 19  # 19 levels between 1 and 20
        heal = heal_base + (heal_per_level * (self.level - 1))
        
        # Movement speed bonus: 20% / 30% / 40% / 50% (based on R rank)
        # If R is not leveled, use base 20%
        ms_bonuses = [20, 30, 40, 50]
        if self.R_ability.current_level == 0:
            ms_bonus = 20
        else:
            ms_bonus = ms_bonuses[self.R_ability.current_level - 1]
        
        return {
            "true_damage": round(true_damage, 2),
            "true_damage_percent": round(true_damage_percent, 2),
            "heal": round(heal, 2),
            "movement_speed_bonus": f"{ms_bonus}%",
            "duration": 1.85
        }

    def Q(self):
        """Lunge - Dash forward and strike an enemy."""
        if self.Q_ability.current_level == 0:
            return {"error": "Ability not learned yet"}
        
        cooldowns = [13, 11.25, 9.5, 7.75, 6]
        base_damages = [70, 80, 90, 100, 110]
        ad_ratios = [0.90, 0.95, 1.00, 1.05, 1.10]
        
        level = self.Q_ability.current_level - 1
        damage = base_damages[level] + (self.bonus_AD * ad_ratios[level])
        
        return {
            "cooldown": cooldowns[level],
            "total_damage": round(damage, 2)
        }
    
    def W(self):
        """Riposte - Parry all damage and counterattack."""
        if self.W_ability.current_level == 0:
            return {"error": "Ability not learned yet"}
        
        cooldowns = [24, 22, 20, 18, 16]
        base_damages = [110, 150, 190, 230, 270]
        
        level = self.W_ability.current_level - 1
        
        return {
            "cooldown": cooldowns[level],
            "magic_damage": base_damages[level]
        }
    
    def E(self):
        """Bladework - Empowered attacks with bonus attack speed."""
        if self.E_ability.current_level == 0:
            return {"error": "Ability not learned yet"}
        
        cooldowns = [11, 10, 9, 8, 7]
        bonus_attack_speeds = [50, 60, 70, 80, 90]
        crit_damages = [160, 170, 180, 190, 200]
        
        level = self.E_ability.current_level - 1
        
        return {
            "cooldown": cooldowns[level],
            "bonus_attack_speed": f"{bonus_attack_speeds[level]}%",
            "critical_damage": f"{crit_damages[level]}%"
        }
    
    def R(self):
        """Grand Challenge - Mark enemy with four vitals."""
        if self.R_ability.current_level == 0:
            return {"error": "Ability not learned yet"}
        
        cooldowns = [110, 90, 70]
        max_heal_bases = [375,500,625]
        bonus_ad_ratio = 3.0
        
        level = self.R_ability.current_level - 1
        max_heal = max_heal_bases[level] + (self.bonus_AD * bonus_ad_ratio)
        return {
            "cooldown": cooldowns[level],
            "heal_per_tick": max_heal[level],
            "heal_bonus_ad_ratio": "15% bonus AD"
        }
    
    def __str__(self):
        base_str = super().__str__()
        abilities_str = f"\nAbilities: Q[{self.Q_ability.current_level}] W[{self.W_ability.current_level}] E[{self.E_ability.current_level}] R[{self.R_ability.current_level}]"
        return base_str + abilities_str

# Usage example
if __name__ == "__main__":
    fiora = Fiora()
    print(fiora)
    print()
    
    # Test passive at level 1
    print("Passive (Duelist's Dance) against 1000 HP target:")
    print(fiora.passive(target_max_hp=1000))
    print()
    
    # Level up and test abilities
    fiora.level_ability('Q')
    fiora.level_ability('W')
    
    for _ in range(5):
        fiora.level_up()
    
    # Unlock ultimate
    fiora.level_ability('R')
    
    print(fiora)
    print("\nPassive (Duelist's Dance) at level 6 with R against 2000 HP target:")
    print(fiora.passive(target_max_hp=2000))
    print()
    
    # Add bonus AD and test again
    fiora.add_stats(bonus_AD=50)
    print(f"After adding 50 bonus AD (Total AD: {fiora.total_AD}):")
    print("Passive against 2000 HP target:")
    print(fiora.passive(target_max_hp=2000))