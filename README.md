# League of Legends Champions Simulator

A Python implementation of League of Legends champion mechanics, starting with Fiora - The Grand Duelist.

## Project Structure

```
lol_champions/
├── __init__.py          # Package initialization
├── champion.py          # Base Champion class
├── ability.py           # Ability class for champion abilities
└── fiora.py            # Fiora champion implementation

main.py                  # Example usage and demonstrations
main_old.py             # Previous version (backup)
README.md               # This file
```

## Features

- **Base Champion System**: Extensible base class with stats and scaling
- **Ability System**: Track ability levels and cooldowns
- **Fiora Implementation**: Complete implementation based on official LoL Wiki data
  - Passive: Duelist's Dance
  - Q: Lunge
  - W: Riposte
  - E: Bladework
  - R: Grand Challenge

## Usage

```python
from lol_champions import Fiora

# Create Fiora instance
fiora = Fiora()

# Level up abilities
fiora.level_ability('Q')
fiora.level_ability('W')

# Use abilities
print(fiora.Q())  # Get Q ability stats
print(fiora.passive(target_max_hp=2000))  # Calculate passive damage

# Level up champion
fiora.level_up()

# Add item stats
fiora.add_stats(bonus_AD=50, bonus_HP=300)
```

## Running the Example

```bash
python main.py
```

## Champion Stats

### Fiora Base Stats
- **Base AD**: 66 (+3.3 per level)
- **Base HP**: 620 (+99 per level)
- **Base Armor**: 33 (+4.7 per level)
- **Base MR**: 32 (+2.05 per level)

### Abilities

#### Passive - Duelist's Dance
- True damage: 3% (+4% per 100 bonus AD) of target's max HP
- Heal: 35-107.65 (based on level)
- Movement speed: 20%/30%/40%/50% (based on R rank)

#### Q - Lunge
- Cooldown: 13/11.25/9.5/7.75/6 seconds
- Damage: 70/80/90/100/110 (+90-110% bonus AD)

#### W - Riposte
- Cooldown: 24/22/20/18/16 seconds
- Magic Damage: 110/150/190/230/270 (+100% AP)

#### E - Bladework
- Cooldown: 11/10/9/8/7 seconds
- Attack Speed: 50/60/70/80/90%
- Crit Damage: 160/170/180/190/200%

#### R - Grand Challenge
- Cooldown: 110/90/70 seconds
- Heal per tick: 18.75/25/31.25 (+15% bonus AD)

## Data Source

All champion data is sourced from the official League of Legends Wiki:
https://wiki.leagueoflegends.com/en-us/Fiora

## Future Enhancements

- Add more champions
- Implement damage calculations against targets
- Add item system
- Simulate combat scenarios
- Add runes and masteries

## License

Educational project for learning Python and game mechanics simulation.
