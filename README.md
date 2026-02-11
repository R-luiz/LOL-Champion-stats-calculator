# League of Legends Fiora Damage Calculator

A Python CLI and library that calculates Fiora's exact post-mitigation damage against any target, including auto attacks, ability combos, and keystone rune interactions. All formulas and values sourced from the official [LoL Wiki](https://wiki.leagueoflegends.com/en-us/).

## Quick Start

```bash
# Single ability damage: Fiora level 9, Q rank 5, 50 bonus AD vs 80 armor target
python cli.py --level 9 --q 5 --bonus-ad 50 --target-armor 80

# Full combo with rune
python cli.py --combo "AA Q passive AA E AA" --level 9 --q 5 --e 1 --bonus-ad 50 --lethality 10 --target-armor 80 --rune pta
```

Output is JSON, designed for easy parsing by Copilot, Claude, or any tool.

## CLI Reference

```
python cli.py [champion options] [item options] [target options] [--rune RUNE] [--combo "STEPS"]
```

### Champion Options

| Flag | Default | Description |
|------|---------|-------------|
| `--level` | 1 | Champion level (1-18) |
| `--q` | 0 | Q (Lunge) rank (0-5) |
| `--w` | 0 | W (Riposte) rank (0-5) |
| `--e` | 0 | E (Bladework) rank (0-5) |
| `--r` | 0 | R (Grand Challenge) rank (0-3, unlocks at level 6/11/16) |

### Item / Stat Options

| Flag | Default | Description |
|------|---------|-------------|
| `--bonus-ad` | 0 | Bonus Attack Damage from items |
| `--bonus-ap` | 0 | Bonus Ability Power from items |
| `--bonus-hp` | 0 | Bonus Health from items |
| `--bonus-ar` | 0 | Bonus Armor from items |
| `--bonus-mr` | 0 | Bonus Magic Resist from items |
| `--lethality` | 0 | Lethality (flat armor penetration) |
| `--armor-pen-pct` | 0 | % Armor Penetration as decimal (0.3 = 30%) |
| `--magic-pen-flat` | 0 | Flat Magic Penetration |
| `--magic-pen-pct` | 0 | % Magic Penetration as decimal (0.4 = 40%) |

### Target Options

| Flag | Default | Description |
|------|---------|-------------|
| `--target-hp` | 2000 | Target's maximum HP |
| `--target-armor` | 80 | Target's total armor |
| `--target-mr` | 50 | Target's total magic resistance |

### Rune Option

`--rune RUNE` where RUNE is one of: `pta`, `conqueror`, `hob`, `grasp`

### Combo Option

`--combo "STEP STEP STEP ..."` where each STEP is one of:

| Step | What it does |
|------|-------------|
| `AA` | Basic auto attack (total AD as physical damage) |
| `Q` | Lunge (physical damage, applies on-hit effects) |
| `W` | Riposte (magic damage) |
| `E` | Bladework crit-empowered auto (total AD * crit multiplier, physical) |
| `passive` | Vital proc (true damage % of target max HP + heal) |

Without `--combo`, the CLI outputs individual damage for each ability. With `--combo`, it simulates the full sequence step by step with rune state tracking.

## Combo Examples

### Short trade (Q poke + vital)
```bash
python cli.py --combo "Q passive" --level 3 --q 2 --target-armor 40
```

### Standard trade with PtA
AA > Q (procs vital) > AA (3rd hit = PtA proc + exposure) > E crit > AA (amped by 8%)
```bash
python cli.py --combo "AA Q passive AA E AA" --level 9 --q 5 --e 1 --bonus-ad 50 --target-armor 80 --rune pta
```

### All-in with R (4 vital procs) + Conqueror
```bash
python cli.py --combo "AA Q passive AA E AA passive AA passive AA passive" --level 11 --q 5 --e 3 --r 2 --bonus-ad 120 --target-armor 100 --rune conqueror
```

### Grasp short trade in lane
```bash
python cli.py --combo "AA passive" --level 3 --q 1 --bonus-ad 10 --target-armor 35 --target-hp 700 --rune grasp
```

### Pure auto attack DPS check (no abilities)
```bash
python cli.py --combo "AA AA AA" --level 6 --bonus-ad 30 --target-armor 60
```

## How Runes Work in Combos

**Press the Attack (pta)**: Stacks on on-hit steps (AA, Q, E). On the 3rd hit, deals 40-174 bonus adaptive damage and exposes the target: all subsequent damage in the combo is amplified by 8%.

**Conqueror**: Every damaging step (except passive) adds 2 stacks (max 12). At max stacks, Fiora gains bonus AD (1.08-2.56 per stack based on level) which increases damage of subsequent abilities, and heals for 8% of post-mitigation damage dealt.

**Hail of Blades (hob)**: Grants 160% bonus attack speed (melee) for 3 attacks. No per-step damage modification in the calculator, but the attack speed info is returned.

**Grasp of the Undying (grasp)**: First on-hit step in the combo deals 3.5% of Fiora's max HP as bonus magic damage and heals for 1.3% max HP. Also grants +5 permanent HP per proc.

## LoL Damage Glossary

These are the core terms used in the damage formulas (from the [LoL Wiki](https://wiki.leagueoflegends.com/en-us/)):

**Damage types:**
- **Physical damage** -- reduced by the target's **armor**. Most auto attacks and AD abilities deal physical damage.
- **Magic damage** -- reduced by the target's **magic resistance (MR)**. Fiora's W (Riposte) deals magic damage.
- **True damage** -- ignores all resistances. Fiora's passive vital procs deal true damage. This is why Fiora is strong against tanks.

**Damage reduction formula** (same for armor and MR):
```
post_mitigation = raw_damage * (100 / (100 + resistance))
```
Example: 200 raw physical damage vs 100 armor = 200 * (100/200) = 100 damage taken. Each point of armor/MR gives 1% more effective HP against that damage type.

**Penetration** (applied in this order):
1. **Flat reduction** -- subtracts a flat amount from resistance (can go negative)
2. **% reduction** -- multiplies remaining resistance by (1 - %)
3. **% penetration** (`--armor-pen-pct`) -- treats target's resistance as lower by this % (only if resistance > 0)
4. **Lethality** (`--lethality`) -- flat armor penetration, subtracts from remaining armor (cannot go below 0)

**Stats:**
- **AD (Attack Damage)** -- determines auto attack damage and scales physical abilities. **Base AD** grows per level; **bonus AD** comes from items.
- **AP (Ability Power)** -- scales magic abilities. Fiora's W scales with AP.
- **Total AD** = base AD + bonus AD. This is what auto attacks use.
- **Bonus AD** = only the AD from items/buffs. Many ability ratios scale with bonus AD specifically (e.g., Fiora Q uses bonus AD, not total AD).

**On-hit** -- effects that trigger when a basic attack (or basic-attack-like ability) hits. Fiora's Q applies on-hit effects, which is why it stacks PtA and procs Grasp. E is an empowered auto attack, also on-hit.

**Adaptive** -- some runes deal "adaptive" damage, meaning physical if your bonus AD >= bonus AP, magic otherwise. Fiora always resolves adaptive as physical (she has 0 base AP).

## Fiora Ability Reference

| Ability | Type | Damage | Scaling |
|---------|------|--------|---------|
| Passive (Duelist's Dance) | True | 3% (+4% per 100 bonus AD) of target max HP | Bonus AD |
| Q (Lunge) | Physical | 70/80/90/100/110 | +90/95/100/105/110% bonus AD |
| W (Riposte) | Magic | 110/150/190/230/270 | +100% AP |
| E (Bladework) | Physical | Total AD * 160/170/180/190/200% crit | Total AD |
| R (Grand Challenge) | -- | Marks 4 vitals (damage = 4x passive procs) | See passive |

## Python API

```python
from lol_champions import Fiora, Target, calculate_damage, calculate_combo
from lol_champions.runes import PressTheAttack

fiora = Fiora()
for _ in range(8): fiora.level_up()
for _ in range(5): fiora.level_ability('Q')
fiora.level_ability('E')
fiora.add_stats(bonus_AD=50, lethality=10)

target = Target(armor=80, mr=50, max_hp=2000)

# Single ability
result = calculate_damage(fiora.Q(), target, champion=fiora)
print(result["total_damage"])  # post-mitigation damage

# Auto attack
aa_result = calculate_damage(fiora.auto_attack(), target, champion=fiora)

# Full combo with rune
pta = PressTheAttack()
combo = calculate_combo(fiora, target, ["AA", "Q", "passive", "AA", "E", "AA"], rune=pta)
print(combo["total_damage"])   # total combo damage including rune procs
print(combo["total_healing"])  # total healing from vitals + rune
```

## Data Source

All champion stats, ability values, damage formulas, and rune numbers from:
https://wiki.leagueoflegends.com/en-us/

## License

Educational project for learning Python and game mechanics simulation.
