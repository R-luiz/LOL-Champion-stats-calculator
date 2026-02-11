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
    
    # Level up abilities
    print("LEVELING ABILITIES")
    print("-" * 40)
    fiora.level_ability('Q')
    fiora.level_ability('W')
    print("Learned Q - Lunge and W - Riposte")
    
    print("\nQ - Lunge:", fiora.Q())
    print("W - Riposte:", fiora.W())
    print("E - Bladework:", fiora.E())
    print("R - Grand Challenge:", fiora.R())
    print()
    
    # Level up champion
    print("LEVELING UP CHAMPION")
    print("-" * 40)
    for i in range(5):
        fiora.level_up()
        if i % 2 == 0:
            fiora.level_ability('Q')
        else:
            fiora.level_ability('E')
    
    # Unlock ultimate at level 6
    fiora.level_ability('R')
    print(f"Leveled up to level {fiora.level}")
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
    
    # Add bonus AD from items
    print("ADDING BONUS STATS (+50 AD)")
    print("-" * 40)
    fiora.add_stats(bonus_AD=50)
    print(f"Total AD: {fiora.total_AD}")
    print()
    
    print("Passive against 2000 HP target with bonus AD:")
    passive_result = fiora.passive(target_max_hp=2000)
    for key, value in passive_result.items():
        print(f"  {key}: {value}")
    print()
    
    print("Q - Lunge with bonus AD:", fiora.Q())
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
