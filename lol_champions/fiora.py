"""Fiora champion implementation."""

from typing import Dict, Union
from .champion import Champion
from .ability import Ability


class Fiora(Champion):
    """Fiora - The Grand Duelist.

    A top lane skirmisher champion that excels at dueling and true damage output.
    Based on official League of Legends Wiki data.
    """

    # Animation / cast time constants (seconds)
    # Q: dash speed ~1100 units over ~400 range ≈ 0.25s at base MS
    Q_CAST_TIME = 0.25
    # W: 0.75s total parry lockout; stab fires at 0.5s into the animation
    W_CAST_TIME = 0.75
    W_HIT_TIME = 0.50
    E_CAST_TIME = 0.0
    R_CAST_TIME = 0.0

    # Vital timing (from LoL Wiki)
    # After proccing a vital: new one identified 0.5s later, takes 1.75s to become targetable
    VITAL_RESPAWN_DELAY = 2.25  # total: 0.5 + 1.75
    # R reveals 4 vitals 0.5s after cast (immediately targetable once they appear)
    R_VITAL_APPEAR_DELAY = 0.5

    # E bonus attack speed by rank (index 0 = rank 1)
    # Bonus AS only applies for the 2 empowered attacks, not a flat duration
    E_BONUS_AS = [50, 60, 70, 80, 90]

    def __init__(self):
        """Initialize Fiora with her base stats."""
        super().__init__(
            base_AD=66,
            AD_scaling=3.3,
            base_AP=0,
            AP_scaling=0,
            base_HP=620,
            HP_scaling=99,
            base_AR=33,
            AR_scaling=4.7,
            base_MR=32,
            MR_scaling=2.05,
            base_AS=0.69,
            AS_ratio=0.69,
            AS_growth=3.2,
            windup_pct=0.1379,
            AS_cap=3.003,
        )
        self.Q_ability = Ability("Lunge", max_level=5)
        self.W_ability = Ability("Riposte", max_level=5)
        self.E_ability = Ability("Bladework", max_level=5)
        self.R_ability = Ability("Grand Challenge", max_level=3)
    
    def level_ability(self, ability: str) -> bool:
        """Level up a specific ability.
        
        Requires an available skill point. Ultimate (R) can only be leveled
        at levels 6, 11, and 16.
        
        Args:
            ability: The ability to level up ('Q', 'W', 'E', or 'R')
            
        Returns:
            True if successful, False otherwise
        """
        if self.skill_points <= 0:
            print(f"No skill points available! Level up to gain skill points.")
            return False
        
        # Check ultimate level restrictions
        if ability == 'R':
            if self.level < 6:
                print("Ultimate can only be learned at level 6 or higher!")
                return False
            if self.R_ability.current_level == 0 and self.level < 6:
                print("Ultimate unlocks at level 6!")
                return False
            if self.R_ability.current_level == 1 and self.level < 11:
                print("Ultimate rank 2 unlocks at level 11!")
                return False
            if self.R_ability.current_level == 2 and self.level < 16:
                print("Ultimate rank 3 unlocks at level 16!")
                return False
        
        # Try to level the ability
        success = False
        if ability == 'Q':
            success = self.Q_ability.level_up()
        elif ability == 'W':
            success = self.W_ability.level_up()
        elif ability == 'E':
            success = self.E_ability.level_up()
        elif ability == 'R':
            success = self.R_ability.level_up()
        
        # Consume skill point if successful
        if success:
            self.skill_points -= 1
            ability_obj = getattr(self, f"{ability}_ability")
            print(f"Leveled up {ability_obj.name} to rank {ability_obj.current_level}! "
                  f"Skill points remaining: {self.skill_points}")
        else:
            if ability in ['Q', 'W', 'E', 'R']:
                ability_obj = getattr(self, f"{ability}_ability")
                print(f"{ability_obj.name} is already at max level!")
        
        return success
    
    def passive(self, target_max_hp: float) -> Dict[str, Union[float, str]]:
        """Duelist's Dance - Hitting a vital deals true damage, heals, and grants movement speed.
        
        Args:
            target_max_hp: The maximum HP of the target whose vital is being hit
            
        Returns:
            Dictionary containing:
                - true_damage: Total true damage dealt
                - true_damage_percent: Percentage of target's max HP
                - heal: Amount Fiora heals
                - movement_speed_bonus: Movement speed bonus percentage
                - duration: Duration of movement speed buff
        """
        # True damage: 3% (+ 4% per 100 bonus AD) of target's maximum health
        base_percent = 3.0
        bonus_ad_scaling = (self.bonus_AD / 100) * 4.0
        true_damage_percent = base_percent + bonus_ad_scaling
        true_damage = (target_max_hp * true_damage_percent) / 100
        
        # Heal: 35 – 107.65 (based on level)
        # Linear interpolation from level 1 (35) to level 20 (107.65)
        heal_base = 35
        heal_max = 107.65
        heal_per_level = (heal_max - heal_base) / 19  # 19 levels between 1 and 20
        heal = heal_base + (heal_per_level * (self.level - 1))
        
        # Movement speed bonus: 20% / 30% / 40% / 50% (based on R rank)
        ms_bonuses = [20, 30, 40, 50]
        if self.R_ability.current_level == 0:
            ms_bonus = 20
        else:
            ms_bonus = ms_bonuses[self.R_ability.current_level - 1]
        
        return {
            "raw_damage": round(true_damage, 2),
            "damage_type": "true",
            "true_damage": round(true_damage, 2),
            "true_damage_percent": round(true_damage_percent, 2),
            "heal": round(heal, 2),
            "movement_speed_bonus": f"{ms_bonus}%",
            "duration": 1.85
        }

    def Q(self) -> Dict[str, Union[float, str]]:
        """Lunge - Dash forward and strike an enemy.
        
        Cost: 20 Mana
        
        Returns:
            Dictionary with cooldown and total damage, or error if not learned
        """
        if self.Q_ability.current_level == 0:
            return {"error": "Ability not learned yet"}
        
        cooldowns = [13, 11.25, 9.5, 7.75, 6]
        base_damages = [70, 80, 90, 100, 110]
        ad_ratios = [0.90, 0.95, 1.00, 1.05, 1.10]
        
        level = self.Q_ability.current_level - 1
        damage = base_damages[level] + (self.bonus_AD * ad_ratios[level])
        
        return {
            "cooldown": cooldowns[level],
            "base_damage": base_damages[level],
            "total_damage": round(damage, 2),
            "raw_damage": round(damage, 2),
            "damage_type": "physical",
            "ad_ratio": f"{int(ad_ratios[level] * 100)}% bonus AD"
        }
    
    def W(self) -> Dict[str, Union[float, str]]:
        """Riposte - Parry all damage and counterattack.
        
        Cost: 50 Mana
        
        Returns:
            Dictionary with cooldown and magic damage, or error if not learned
        """
        if self.W_ability.current_level == 0:
            return {"error": "Ability not learned yet"}
        
        cooldowns = [24, 22, 20, 18, 16]
        base_damages = [110, 150, 190, 230, 270]
        
        level = self.W_ability.current_level - 1
        damage = base_damages[level] + self.total_AP  # 100% AP ratio

        return {
            "cooldown": cooldowns[level],
            "magic_damage": base_damages[level],
            "raw_damage": round(damage, 2),
            "damage_type": "magic",
            "ap_ratio": "100% AP"
        }
    
    def E(self) -> Dict[str, Union[float, str]]:
        """Bladework - Empowered attacks with bonus attack speed.
        
        Cost: 40 Mana
        
        Returns:
            Dictionary with cooldown, attack speed, and crit damage, or error if not learned
        """
        if self.E_ability.current_level == 0:
            return {"error": "Ability not learned yet"}
        
        cooldowns = [11, 10, 9, 8, 7]
        bonus_attack_speeds = [50, 60, 70, 80, 90]
        crit_damages = [160, 170, 180, 190, 200]
        
        level = self.E_ability.current_level - 1
        crit_multiplier = crit_damages[level] / 100.0
        empowered_damage = self.total_AD * crit_multiplier

        return {
            "cooldown": cooldowns[level],
            "bonus_attack_speed": f"{bonus_attack_speeds[level]}%",
            "critical_damage": f"{crit_damages[level]}%",
            "raw_damage": round(empowered_damage, 2),
            "damage_type": "physical",
        }
    
    def R(self) -> Dict[str, Union[float, str]]:
        """Grand Challenge - Mark enemy with four vitals.
        
        Cost: 100 Mana
        
        Returns:
            Dictionary with cooldown and healing info, or error if not learned
        """
        if self.R_ability.current_level == 0:
            return {"error": "Ability not learned yet"}
        
        cooldowns = [110, 90, 70]
        heal_per_tick = [18.75, 25, 31.25]
        
        level = self.R_ability.current_level - 1
        
        return {
            "cooldown": cooldowns[level],
            "heal_per_tick": heal_per_tick[level],
            "heal_bonus_ad_ratio": "15% bonus AD",
            "duration": "5 seconds"
        }
    
    def e_bonus_attack_speed(self) -> float:
        """Return E's bonus attack speed % at current rank, or 0 if not learned."""
        if self.E_ability.current_level == 0:
            return 0.0
        return self.E_BONUS_AS[self.E_ability.current_level - 1]

    def get_cooldown(self, ability: str) -> float:
        """Return cooldown in seconds for the given ability at current rank.

        Returns float('inf') if ability is not learned.
        """
        cooldowns = {
            'Q': [13, 11.25, 9.5, 7.75, 6],
            'W': [24, 22, 20, 18, 16],
            'E': [11, 10, 9, 8, 7],
            'R': [110, 90, 70],
        }
        ab = getattr(self, f"{ability}_ability")
        if ab.current_level == 0:
            return float('inf')
        return cooldowns[ability][ab.current_level - 1]

    def __str__(self) -> str:
        """String representation including abilities."""
        base_str = super().__str__()
        abilities_str = (f"\nAbilities: Q[{self.Q_ability.current_level}] "
                        f"W[{self.W_ability.current_level}] "
                        f"E[{self.E_ability.current_level}] "
                        f"R[{self.R_ability.current_level}]")
        return base_str + abilities_str
