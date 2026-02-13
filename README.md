# League of Legends Fiora Damage Calculator

A Python CLI and library that calculates Fiora's exact post-mitigation damage against any target, including auto attacks, ability combos, keystone rune interactions, sustain healing, and time-based DPS optimization. Includes a **live mode** that reads your in-game stats in real time via the Riot Live Client Data API. All formulas and values sourced from the official [LoL Wiki](https://wiki.leagueoflegends.com/en-us/). Pure Python, no external dependencies.

## Copilot / AI Assistant Prompt

Use this as your system prompt when asking Fiora damage questions:

> You are a League of Legends Fiora damage assistant. You answer questions by running `python cli.py` from this repository and interpreting the JSON output.
>
> **Rules:**
> 1. Never ask clarifying questions. Use reasonable defaults for anything not specified: level 9, Q rank 5, E rank 3, W rank 1, R rank 1, 50 bonus AD, 80 target armor, 50 target MR, 2000 target HP.
> 2. Translate the user's LoL language into CLI flags. "I have Triforce" → `--bonus-ad 45 --bonus-as 33`. "I have Spear of Shojin" → `--bonus-ad 45 --bonus-hp 450 --shojin-stacks 0` (stacks start at 0 in DPS/combo, set higher for mid-fight snapshots). "Enemy has Plated Steelcaps + 2 cloth armors" → `--target-armor 110`. Look up item stats if needed.
> 3. Pick the right mode automatically:
>    - "How much does Q do?" → default mode (no --combo, no --time)
>    - "How much damage does AA Q passive AA E AA do?" → `--combo "AA Q passive AA E AA"`
>    - "What's my max damage in 5 seconds?" or "DPS in a 5s trade?" → `--time 5`
> 4. Always include the rune flag if the user mentions a keystone. Map common names: "PtA" / "Press the Attack" → `--rune pta`, "Conq" → `--rune conqueror`, "HoB" → `--rune hob`, "Grasp" → `--rune grasp`.
> 5. Add minor rune flags when mentioned: "Last Stand" → `--last-stand MISSING_HP_PCT` (e.g. `--last-stand 50` means 50% HP missing = 50% current HP). "Coup de Grace" → `--coup-de-grace TARGET_HP_PCT` (e.g. `--coup-de-grace 35` means target is at 35% HP). "Cut Down" → `--cut-down` (auto-calculated from target/champion HP difference). If the user says "I'm low" or "execute range", use `--last-stand 70` or `--coup-de-grace 30` as reasonable estimates.
> 6. For DPS mode (`--time`), include `--bonus-as` if the user has attack speed items. Use `--r-active` only if R was already cast before the fight (4 vitals immediately). Without `--r-active`, the optimizer will still activate R mid-fight on its own if R is ranked — so just having `--r 1` is enough for "I ult them" or "all-in" scenarios.
> 7. Answer with the final number first (e.g. "Q deals 91.67 post-mitigation damage"), then optionally a one-line breakdown. Do not dump raw JSON.
> 8. Rune interactions are automatic: PtA stacks on AA/Q/E and procs on 3rd hit with 8% amp after; Conqueror stacks +2 per action, grants bonus AD at 12 stacks which also increases vital true damage; Grasp procs on first on-hit. In DPS mode, vitals auto-proc on damaging actions when available (2.25s respawn); the optimizer will wait for vital respawn when the vital value (damage + heal) outweighs the time spent idle. In combo mode, you must explicitly include `passive` steps where vitals would proc.
> 9. E in combos = Bladework crit-empowered auto. In DPS mode, E is split into E_ACTIVATE (instant, resets AA timer) + E_FIRST (non-crit empowered auto) + E_CRIT (guaranteed crit). R_ACTIVATE is used automatically when optimal.
> 10. DPS output includes a `timeline` array with per-action timestamps and a `sequence` string. Use these to describe the optimal rotation (e.g. "E > E_FIRST > Q > E_CRIT > AA > AA" at specific timings).
> 11. Damage modifiers (Last Stand, Coup de Grace, Cut Down, Shojin) stack multiplicatively with each other and with rune amps. The output includes `amp_multiplier` per step and `damage_modifiers` in the top-level result.
> 12. Shojin in combo/DPS mode tracks stacks dynamically: starts at `--shojin-stacks N`, each ability cast grants a stack (max 4), the triggering ability does NOT benefit from its own stack. In default mode (single ability), the stacks value is applied as a static amp.
> 13. If the user asks to compare scenarios, run multiple commands and present a comparison table.

## Quick Start

```bash
# Single ability damage: Fiora level 9, Q rank 5, 50 bonus AD vs 80 armor target
python cli.py --level 9 --q 5 --bonus-ad 50 --target-armor 80

# Full combo with rune
python cli.py --combo "AA Q passive AA E AA" --level 9 --q 5 --e 1 --bonus-ad 50 --lethality 10 --target-armor 80 --rune pta

# Live mode: real-time dashboard during a game
python live.py --target Darius --time 5

# Demo: see the live dashboard without a running game
python demo_live.py
```

Output from `cli.py` is JSON, designed for easy parsing by Copilot, Claude, or any tool. `live.py` outputs a refreshing terminal dashboard.

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

### Rune Options

`--rune RUNE` where RUNE is one of: `pta`, `conqueror`, `hob`, `grasp`

#### Minor Runes (Damage Modifiers)

| Flag | Default | Description |
|------|---------|-------------|
| `--last-stand` | -- | Last Stand: your missing HP % (0-100). 5% amp at 60% HP, scales to 11% at 30% HP |
| `--coup-de-grace` | -- | Coup de Grace: target current HP % (0-100). 8% amp if target < 40% HP |
| `--cut-down` | false | Cut Down: 5-15% amp based on target vs champion max HP difference (auto-calculated) |

All minor rune amps stack multiplicatively with each other and with keystone effects.

### Item Passives

| Flag | Default | Description |
|------|---------|-------------|
| `--shojin-stacks` | -- | Spear of Shojin initial stacks (0-4). 3% per stack on ability/proc damage. In combo/DPS mode, stacks build dynamically per ability cast |

Remember to also add Shojin's raw stats: `--bonus-ad 45 --bonus-hp 450`.

### Combo Option

`--combo "STEP STEP STEP ..."` where each STEP is one of:

| Step | What it does |
|------|-------------|
| `AA` | Basic auto attack (total AD as physical damage) |
| `Q` | Lunge (physical damage, applies on-hit effects) |
| `W` | Riposte (magic damage) |
| `E` | Bladework crit-empowered auto (total AD * crit multiplier, physical) |
| `passive` | Vital proc (true damage % of target max HP + heal) |

Without `--combo` or `--time`, the CLI outputs individual damage for each ability. With `--combo`, it simulates the full sequence step by step with rune state tracking. With `--time`, it finds the optimal action sequence for maximum damage.

In DPS mode, E is automatically split into three phases: **E_ACTIVATE** (instant, resets AA timer, grants bonus AS for 2 attacks), **E_FIRST** (first empowered auto, no crit), and **E_CRIT** (second empowered auto, guaranteed crit). **R_ACTIVATE** is used when it maximizes damage (reveals 4 vitals after 0.5s).

### DPS Optimizer Options

| Flag | Default | Description |
|------|---------|-------------|
| `--time` | -- | Time window in seconds to optimize over (e.g. `--time 5`) |
| `--bonus-as` | 0 | Bonus attack speed % from items (e.g. 35 for 35%) |
| `--r-active` | false | R is active (4 vitals available immediately) |

DPS mode uses branch-and-bound search (<=10s) or greedy heuristic (>10s) to find the action sequence that maximizes total damage. It accounts for attack speed, ability cooldowns, cast times, AA resets (Q and E), vital respawn timing (2.25s between passive procs), R activation (4 vitals after 0.5s delay), E two-attack model (E_FIRST + E_CRIT with bonus AS only during empowered attacks), all rune interactions, and damage modifiers (Last Stand, Coup de Grace, Cut Down, Spear of Shojin).

The optimizer maximizes vital procs by considering waiting for vital respawn when the vital value (damage + heal) outweighs the idle time cost. In short burst windows where no vital will respawn, it prioritizes raw burst instead. Shojin stacks build dynamically per ability cast during the optimized sequence.

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

## DPS Optimizer Examples

### 5-second trade with PtA
```bash
python cli.py --time 5 --level 9 --q 5 --e 3 --bonus-ad 50 --target-armor 80 --rune pta
```

### 8-second all-in with R active + Conqueror
```bash
python cli.py --time 8 --level 11 --q 5 --w 1 --e 3 --r 2 --bonus-ad 120 --target-armor 100 --target-mr 60 --target-hp 3000 --r-active --rune conqueror
```

### Long DPS check with attack speed items
```bash
python cli.py --time 15 --level 14 --q 5 --e 5 --r 2 --bonus-ad 200 --bonus-as 50 --target-armor 150
```

### Spear of Shojin combo (stacks build per ability cast)
```bash
python cli.py --combo "Q passive AA E AA Q passive" --level 9 --q 5 --e 3 --bonus-ad 95 --bonus-hp 450 --target-armor 80 --shojin-stacks 0
```

### DPS with Last Stand at 50% missing HP + Shojin
```bash
python cli.py --time 6 --level 14 --q 5 --e 5 --r 2 --bonus-ad 195 --bonus-hp 450 --target-armor 100 --target-hp 3000 --last-stand 50 --shojin-stacks 0 --r-active
```

### Coup de Grace vs low HP target
```bash
python cli.py --level 9 --q 5 --bonus-ad 50 --target-armor 80 --target-hp 800 --coup-de-grace 30
```

### Cut Down vs tanky target
```bash
python cli.py --time 8 --level 14 --q 5 --e 5 --r 2 --bonus-ad 150 --target-armor 200 --target-hp 4000 --cut-down --rune conqueror
```

## Live Mode (`live.py`)

Real-time damage calculator that reads your Fiora's stats directly from the in-game client during a League of Legends match. No manual stat entry needed — it auto-detects your level, ability ranks, items, runes, and sustain stats every poll cycle.

### How It Works

1. Connects to the Riot Live Client Data API at `https://127.0.0.1:2999` (available while a game is running)
2. Reads your champion stats, items, abilities, and runes via the `/activeplayer` and `/playerlist` endpoints
3. Fetches enemy champion base stats from Riot's Data Dragon CDN to auto-estimate target armor/MR/HP
4. Computes per-ability damage, per-ability healing, DPS optimizer results, and kill combo timing
5. Refreshes the terminal dashboard every 2 seconds (configurable)

### Live Mode Options

| Flag | Default | Description |
|------|---------|-------------|
| `--target` | first enemy | Enemy champion name to track (e.g. `Darius`) |
| `--target-hp` | auto | Manual target HP override |
| `--target-armor` | auto | Manual target armor override |
| `--target-mr` | auto | Manual target MR override |
| `--interval` | 2 | Poll interval in seconds |
| `--time` | -- | Include DPS optimizer with this time window (e.g. `5`) |

### Usage Examples

```bash
# Auto-detect everything, default target (first enemy)
python live.py

# Track a specific enemy, include 5s DPS optimizer
python live.py --target Darius --time 5

# Manual target stats override
python live.py --target-armor 120 --target-hp 3000

# Mix auto-estimation with manual overrides
python live.py --target Darius --target-armor 150

# Faster refresh rate
python live.py --interval 1 --time 5
```

### Target HP Calibration

On first detecting an enemy champion, live mode prompts you to enter their actual max HP (visible by clicking them in-game). It compares this to its base+items estimate to deduce which rune stat shards they're running (flat +65 HP, scaling +10-180, both, or none), then scales the shard HP correctly as they level up throughout the game. If you skip the prompt, it defaults to a common shard combo (scaling + flat 65).

### Dashboard Display

The live dashboard shows:

- **Champion info**: level, ability ranks, total AD, attack speed
- **Runes**: auto-detected keystone and minor runes
- **HP**: current / max with percentage
- **Sustain**: life steal %, omnivamp %, health regen/s (from items)
- **Items**: current item build
- **Target**: enemy name, level, shard estimation, armor/MR/HP
- **Per-ability damage**: each ability's post-mitigation damage as raw number and % of target HP
- **Per-ability healing**: sustain healing from each ability (life steal on AA/Q/E, omnivamp on all)
- **PtA variants**: damage and healing with PtA 8% exposure applied (shown in brackets)
- **DPS optimizer**: optimal rotation, total damage, DPS, total healing (if `--time` is set)
- **Kill combo**: fastest sequence to kill the target from full HP, with hit count and total healing

### Sustain Tracking

Live mode reads three sustain stats from the API and integrates them into all calculations:

- **Life Steal** (`lifeSteal`): heals on on-hit physical damage (AA, Q, E). Does NOT heal from W
- **Omnivamp** (`spellVamp` in the API): heals on ALL post-mitigation damage (physical, magic, true) at full effectiveness for single-target abilities
- **Health Regen** (`healthRegenRate`): passive HP/sec, applied as `rate * duration` in the DPS optimizer

Per-ability healing is shown next to each ability's damage:
- With PtA: `heal: (normal / with_pta)` — both values shown
- Without PtA: `heal: value`
- Vital: includes the flat passive heal + omnivamp on the true damage

The DPS optimizer and kill combo also track total healing across the full sequence.

### Data Dragon Integration

Live mode uses Riot's Data Dragon CDN (`ddragon.leagueoflegends.com`) to fetch:

- **Enemy champion base stats**: HP, armor, MR at any level using the LoL scaling formula
- **Item stats**: HP, armor, MR, AD, AP, attack speed from item IDs on the scoreboard
- **Target estimation**: combines champion base stats + item bonuses + calibrated shard HP

Data is cached locally at `~/.cache/lol_data/<version>/` so subsequent launches are instant. The game version is auto-detected.

## Demo Script (`demo_live.py`)

Simulates the live dashboard without a running game, useful for testing or previewing the display.

```bash
python demo_live.py
```

The demo sets up a level 14 Fiora with Doran's Blade, Ravenous Hydra, and Endless Hunger against a Darius target (2800 HP, 152 armor, 58 MR) with Press the Attack and Last Stand.

## How Runes Work

Rune interactions are fully tracked in both combo and DPS modes.

**Press the Attack (pta)**: Stacks on on-hit actions (AA, Q, E). On the 3rd hit, deals 40-174 bonus adaptive damage and exposes the target: all subsequent damage is amplified by 8%, including vital true damage.

**Conqueror**: Every damaging action (except passive) adds 2 stacks (max 12). At max stacks, Fiora gains bonus AD (1.08-2.56 per stack based on level) which increases ability damage AND vital true damage (passive scales with bonus AD). Heals for 8% of all damage dealt (ability + vital combined).

**Hail of Blades (hob)**: Grants 160% bonus attack speed (melee) for 3 attacks. In DPS mode, this reduces attack intervals during burst, allowing faster AA/E_CRIT weaving.

**Grasp of the Undying (grasp)**: First on-hit action deals 3.5% of Fiora's max HP as bonus magic damage and heals for 1.3% max HP. Also grants +5 permanent HP per proc.

### Minor Runes (Precision Row 3)

These are damage amplifiers that stack multiplicatively with keystones and each other.

**Last Stand**: 5% increased damage below 60% HP, scaling to 11% at 30% HP. Linear interpolation between thresholds. Applies to all damage types including true damage (since patch 15.3).

**Coup de Grace**: 8% increased damage to targets below 40% max HP. Binary threshold — full amp or nothing.

**Cut Down**: 5-15% increased damage to targets with more max HP than you. Scales linearly from 5% (target has 10% more HP) to 15% (100% more HP).

### Item Passives

**Spear of Shojin**: Focused Will grants a stack per ability cast (max 4). Each stack amplifies ability and proc damage by 3% (up to 12%). Does NOT amplify basic auto attacks. Does NOT grant stacks from passive procs. The triggering ability does NOT benefit from its own stack — the first ability cast deals unamplified damage, the second benefits from 1 stack, etc.

## Item Proc System (29 Items)

The damage engine models proc effects for 29 items across 8 categories. All procs are automatically integrated into the DPS optimizer and build optimizer — you only need to pass item instances and the engine handles proc timing, cooldowns, and stacking.

### On-Hit Items
| Item | Damage |
|------|--------|
| Blade of the Ruined King | 9% (melee) / 6% (ranged) target current HP as physical. **Dynamically tracks target HP** — damage decreases per hit as HP drops |
| Wit's End | 45 bonus magic damage |
| Nashor's Tooth | 15 + 15% AP magic damage |
| Recurve Bow | 15 physical damage |
| Terminus | 30 magic damage (Light/Dark alternation) |
| Titanic Hydra | 5 + 1% max HP physical on-hit + active (10s CD) |

### Stacking On-Hit
| Item | Damage |
|------|--------|
| Kraken Slayer | Every 3rd hit: 150-210 (melee, scales with level) bonus physical |

### Spellblade (Exclusive — max 1 per build)
| Item | Damage |
|------|--------|
| Trinity Force | 200% base AD bonus physical (1.5s CD) |
| Iceborn Gauntlet | 150% base AD bonus physical + slow (1.5s CD) |
| Lich Bane | 75% base AD + 40% AP magic damage (1.5s CD) |

### Energized (Stack from AAs, proc at 100 stacks)
| Item | Damage |
|------|--------|
| Voltaic Cyclosword | 100 physical + slow |
| Rapid Firecannon | 40 magic + bonus range |
| Statikk Shiv | 60 magic, chain-lightning |
| Stormrazor | 100 magic + bonus MS |

### Active Items
| Item | Damage |
|------|--------|
| Profane Hydra | 80% AD physical (10s CD, AA reset) |
| Ravenous Hydra | 80% AD physical (10s CD, AA reset) |
| Stridebreaker | 80% total AD physical (15s CD) |
| Hextech Rocketbelt | 100 + 10% AP magic (40s CD) |
| Everfrost | 300 + 85% AP magic (30s CD) |
| Hextech Gunblade | 175-253 + 30% AP magic (40s CD) |

### Burn / Immolate
| Item | Damage |
|------|--------|
| Liandry's Torment | 6% target max HP magic per ability hit (over 3s) |
| Sunfire Aegis | 20 + 1% bonus HP magic DPS aura (immolate, exclusive) |
| Hollow Radiance | 15 + 1% bonus HP magic DPS aura (immolate, exclusive) |

### Conditional
| Item | Damage |
|------|--------|
| Sundered Sky | First AA vs champ: guaranteed crit + heal (10s CD) |
| Dead Man's Plate | At full momentum: 40 + 120% base AD bonus physical (first hit only) |

### Damage Amplifier
| Item | Effect |
|------|--------|
| Lord Dominik's Regards | 0-15% increased damage vs champs based on bonus HP difference |
| Spear of Shojin | 3% per stack (max 4) on ability/proc damage |

### Stat-Only (No Proc)
Death's Dance, Sterak's Gage, Maw of Malmortius, Guardian Angel, Experimental Hexplate — included in the build optimizer catalog for their raw stats.

### Amplification Pipeline

All item procs are correctly amplified by all damage sources:

- **Static modifiers** (Last Stand, Coup de Grace, Cut Down): baked into all pre-computed proc values
- **PtA exposure** (8% after 3 hits): applied dynamically to every item proc while target is exposed
- **Immolate DPS**: amplified by both static modifiers and PtA (proportional to exposed duration)
- **Conqueror bonus AD**: affects ability base damage at max stacks (item procs that don't scale with AD are unaffected, which is correct)
- **Shojin stacks**: amplifies ability damage (Q/W/E) and vital true damage, not on-hit procs

## Build Optimizer

Automatically searches over item combinations to find the highest-DPS build for a given champion, target, and time window. All item stats and proc effects are applied and removed automatically per combination.

### Usage

```python
from lol_champions import Fiora, Target, optimize_build
from lol_champions.runes import PressTheAttack

fiora = Fiora()
for _ in range(10): fiora.level_up()
for _ in range(5): fiora.level_ability('Q')
fiora.level_ability('W')
fiora.level_ability('E')
fiora.level_ability('R')

target = Target(max_hp=2000, armor=80, mr=50)

# Find the best 2-item build in a 4s window
builds = optimize_build(
    champion=fiora, target=target, time_limit=4.0,
    item_count=2, rune=PressTheAttack(),
    pool=["Blade of the Ruined King", "Profane Hydra", "Trinity Force",
          "Kraken Slayer", "Wit's End", "Spear of Shojin"],
    top_n=5,
)
for i, b in enumerate(builds, 1):
    print(f"  #{i}: {' + '.join(b['items'])}  —  {b['dps']} DPS")
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `champion` | required | Champion instance at desired level |
| `target` | required | Target with HP/armor/MR |
| `time_limit` | required | Combo duration in seconds |
| `item_count` | required | Number of items to optimize (1-6) |
| `rune` | None | Keystone rune instance |
| `damage_modifiers` | None | Static amps (Last Stand, etc.) |
| `pool` | all items | Whitelist of item names to consider |
| `exclude` | None | Blacklist of item names |
| `strategy` | "auto" | `"exhaustive"` / `"greedy"` / `"auto"` |
| `top_n` | 5 | Number of top builds to return |
| `r_active` | False | R pre-activated (4 vitals immediately) |

### Search Strategies

- **Exhaustive** (default for 1-3 items): tries every valid combination. Globally optimal but slower (~3-4 min for 3 items from 25 pool).
- **Greedy** (default for 4-6 items): picks the best item per slot iteratively. Fast (~15s for 6 items) but may miss synergies.
- **Auto**: selects exhaustive for ≤3 items, greedy for 4+.

### Exclusive Groups

The optimizer enforces item uniqueness constraints:
- **Spellblade**: max 1 of Trinity Force / Iceborn Gauntlet / Lich Bane
- **Hydra**: max 1 of Titanic / Profane / Ravenous Hydra / Tiamat
- **Immolate**: max 1 of Sunfire Aegis / Hollow Radiance
- No duplicate items

### Item Catalog Validation

Compare hardcoded item stats against Riot's Data Dragon to detect patch drift:

```python
from lol_champions import validate_catalog, DataDragon
dd = DataDragon()
validate_catalog(dd)  # prints warnings for any stat mismatches
```

## Logging

Detailed calculation logs are saved to the `logs/` directory.

### Single DPS Result

```python
from lol_champions import log_result
path = log_result(result, champion=fiora, target=target,
                  items=["BotRK", "Profane Hydra"], rune="PressTheAttack")
```

### Build Optimizer Results

```python
from lol_champions import log_build_results
path = log_build_results(builds, champion=fiora, target=target,
                         rune="PressTheAttack", time_limit=4.0)
```

### Log Format

Logs include a full header (champion stats, ability ranks, target, rune), a rankings table for build optimizer runs, and per-action timelines with damage/healing breakdowns:

```
    0.00s  AA            dmg=  371.5  heal=  91.8  BotRK(111), vital(140.0)
    0.95s  AA            dmg=  210.8  heal=  16.9  BotRK(90)
    1.08s  HYDRA_ACTIVE  dmg=  104.0  heal=   0.0  AA-reset, dmg(104)
    ...
```

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
from lol_champions import (
    Fiora, Target, calculate_damage, calculate_combo, optimize_dps,
    optimize_build, validate_catalog, log_result, log_build_results,
)
from lol_champions.runes import PressTheAttack
from lol_champions.runes import LastStand, CoupDeGrace, CutDown
from lol_champions.items import (
    SpearOfShojin, BladeOfTheRuinedKing, TrinityForce,
    ProfaneHydra, WitsEnd, KrakenSlayer,
)

fiora = Fiora()
for _ in range(8): fiora.level_up()
for _ in range(5): fiora.level_ability('Q')
fiora.level_ability('E')
fiora.add_stats(bonus_AD=50, lethality=10)

target = Target(armor=80, mr=50, max_hp=2000)

# Single ability
result = calculate_damage(fiora.Q(), target, champion=fiora)
print(result["total_damage"])  # post-mitigation damage

# Single ability with damage modifiers
ls = LastStand()
mods = [{"name": "Last Stand", "amp": ls.damage_amp(missing_hp_pct=50)}]
result = calculate_damage(fiora.Q(), target, champion=fiora, damage_modifiers=mods)
print(result["total_damage"])         # amped damage
print(result["total_amp_multiplier"]) # total multiplier applied

# Full combo with rune + Shojin (stacks build dynamically)
pta = PressTheAttack()
shojin = SpearOfShojin(stacks=0)
combo = calculate_combo(
    fiora, target, ["AA", "Q", "passive", "AA", "E", "AA"],
    rune=pta, damage_modifiers=mods, items=[shojin],
)
print(combo["total_damage"])   # total combo damage including rune procs
print(combo["total_healing"])  # total healing from vitals + rune

# DPS optimizer with item procs: Trinity + BotRK + Shojin
items_list = [TrinityForce(), BladeOfTheRuinedKing(), SpearOfShojin()]
fiora.add_stats(bonus_AD=35+40, bonus_HP=300, bonus_AS=33+25, life_steal=0.08)
dps = optimize_dps(
    fiora, target, time_limit=5.0, rune=pta,
    damage_modifiers=mods, items=items_list,
)
print(dps["total_damage"])     # optimal total damage
print(dps["dps"])              # damage per second
print(dps["sequence"])         # optimal action sequence
print(dps["total_healing"])    # total healing (sustain + vitals + rune)
fiora.add_stats(bonus_AD=-(35+40), bonus_HP=-300, bonus_AS=-(33+25), life_steal=-0.08)

# Build optimizer: find best 2-item build automatically
builds = optimize_build(
    fiora, target, time_limit=5.0, item_count=2, rune=pta,
    pool=["Trinity Force", "Blade of the Ruined King", "Profane Hydra",
          "Kraken Slayer", "Wit's End", "Spear of Shojin"],
)
for b in builds:
    print(f"  {' + '.join(b['items'])}  —  {b['dps']} DPS")

# Log results to files
log_result(dps, champion=fiora, target=target,
           items=["Trinity Force", "BotRK"], rune="PressTheAttack")
log_build_results(builds, champion=fiora, target=target,
                  rune="PressTheAttack", time_limit=5.0)

# Sustain stats: life steal, omnivamp, health regen
fiora.add_stats(life_steal=0.10, omnivamp=0.05, health_regen_per_sec=8.5)
# Or set directly (e.g. from API total values):
fiora.life_steal = 0.10         # 10% life steal
fiora.omnivamp = 0.085          # 8.5% omnivamp
fiora.health_regen_per_sec = 14.2
# Sustain is integrated into the DPS optimizer automatically
```

### Live Client API

```python
from lol_champions.live_client import is_game_active, get_active_player, get_player_list
from lol_champions.data_dragon import DataDragon

# Check if a game is running
if is_game_active():
    player = get_active_player()    # your stats, abilities, runes
    players = get_player_list()     # all 10 players' scoreboard data

# Fetch enemy base stats from Data Dragon
dd = DataDragon()                            # auto-detects game version
stats = dd.champion_stats_at_level("Darius", 14)  # {"hp", "armor", "mr", "ad"}
target = dd.estimate_target("Darius", 14, [3071, 3143])  # base + item bonuses
```

## Project Structure

```
cli.py                          # JSON CLI for manual stat input
live.py                         # Real-time dashboard (Live Client Data API)
demo_live.py                    # Demo script (simulated live display)
main.py                         # Quick demo script

lol_champions/
  champion.py                   # Base Champion class (stats, scaling, sustain)
  fiora.py                      # Fiora subclass (abilities, passives, timing)
  ability.py                    # Ability dataclass
  target.py                     # Target dataclass
  damage.py                     # Damage engine (penetration, mitigation, modifiers)
  dps.py                        # DPS optimizer (branch-and-bound / greedy)
  runes.py                      # Keystones + minor runes
  items.py                      # 29 item proc dataclasses (on-hit, spellblade, energized, burn, active, conditional)
  build_optimizer.py            # Build optimizer (exhaustive / greedy search over item combinations)
  logger.py                     # Detailed calculation logging to files
  live_client.py                # Riot Live Client Data API client
  data_dragon.py                # Data Dragon CDN fetcher + cache

logs/                           # Generated calculation logs (git-ignored)
```

## Data Source

All champion stats, ability values, damage formulas, and rune numbers from:
https://wiki.leagueoflegends.com/en-us/

## License

Educational project for learning Python and game mechanics simulation.
