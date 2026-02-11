"""Example usage of the Fiora champion."""

from lol_champions import Fiora


def main():
    """Demonstrate Fiora's abilities and stats."""
    print("=" * 60)
    print("FIORA - THE GRAND DUELIST")
    print("=" * 60)
    
    # Create Fiora instance
    fiora = Fiora()
    print(f"\n{fiora}")
    print()
    
    # Test passive at level 1
    print("PASSIVE - Duelist's Dance")
    print("-" * 40)
    print("Against 1000 HP target:")
    passive_result = fiora.passive(target_max_hp=1000)
    for key, value in passive_result.items():
        print(f"  {key}: {value}")
    print()
    
    # Try to level up abilities without points
    print("TRYING TO LEVEL WITHOUT SKILL POINTS")
    print("-" * 40)
    fiora.level_ability('Q')
    print()
    
    # Level up champion to gain ability points
    print("LEVELING UP CHAMPION")
    print("-" * 40)
    fiora.level_up()  # Level 2
    fiora.level_ability('Q')
    print()
    
    fiora.level_up()  # Level 3
    fiora.level_ability('W')
    print()
    
    fiora.level_up()  # Level 4
    fiora.level_ability('Q')
    print()
    
    fiora.level_up()  # Level 5
    fiora.level_ability('E')
    print()
    
    # Try to unlock ultimate before level 6
    print("TRYING TO UNLOCK ULTIMATE EARLY")
    print("-" * 40)
    fiora.level_ability('R')
    print()
    
    # Level up to 6 and unlock ultimate
    print("REACHING LEVEL 6")
    print("-" * 40)
    fiora.level_up()  # Level 6
    fiora.level_ability('R')
    print()
    
    print(f"\n{fiora}")
    print()
    
    print("ABILITIES AT LEVEL 6")
    print("-" * 40)
    print("Passive against 2000 HP target:")
    passive_result = fiora.passive(target_max_hp=2000)
    for key, value in passive_result.items():
        print(f"  {key}: {value}")
    print()
    
    print("Q - Lunge:", fiora.Q())
    print("W - Riposte:", fiora.W())
    print("E - Bladework:", fiora.E())
    print("R - Grand Challenge:", fiora.R())
    print()
    
    # Continue leveling
    print("CONTINUING TO LEVEL UP")
    print("-" * 40)
    for i in range(5):  # Level 7-11
        fiora.level_up()
        if i % 2 == 0:
            fiora.level_ability('Q')
        else:
            fiora.level_ability('E')
    
    # Level ultimate at level 11
    fiora.level_ability('R')
    print()
    
    # Add bonus AD from items
    print("ADDING BONUS STATS (+50 AD)")
    print("-" * 40)
    fiora.add_stats(bonus_AD=50)
    print(f"Total AD: {fiora.total_AD}")
    print()
    
    print(f"\n{fiora}")
    print()
    
    print("FINAL ABILITIES")
    print("-" * 40)
    print("Passive against 2000 HP target with bonus AD:")
    passive_result = fiora.passive(target_max_hp=2000)
    for key, value in passive_result.items():
        print(f"  {key}: {value}")
    print()
    
    print("Q - Lunge:", fiora.Q())
    print("R - Grand Challenge:", fiora.R())
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
