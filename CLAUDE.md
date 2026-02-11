# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

League of Legends Champion Simulator with damage calculation engine. Models champion mechanics, stats, abilities, runes, and computes post-mitigation damage against targets. Currently implements Fiora. Pure Python, no external dependencies.

## Commands

```bash
# Run the main demo
python main.py
```

No build step, test framework, or linter is configured.

## Architecture

```
Champion (dataclass, base class) ──→ Fiora (subclass, concrete champion)
    uses ──→ Ability (dataclass, tracks level/max_level per ability slot)

Target (dataclass) ── damage target with HP/armor/MR
    Target.from_champion() ── use a Champion as target

calculate_damage(ability_data, target, champion) ── core damage pipeline
    uses ──→ effective_resistance() ── penetration order of operations
    uses ──→ damage_after_mitigation() ── LoL armor/MR formula

Runes (dataclasses): PressTheAttack, Conqueror, HailOfBlades, GraspOfTheUndying
    proc dicts include raw_damage + damage_type ── passable to calculate_damage()
```

### Key Files

- **`lol_champions/champion.py`** — Base `Champion` dataclass: 5 core stats (AD, AP, HP, AR, MR) each with base/scaling/bonus/total fields, plus penetration stats (lethality, armor_pen_pct, magic_pen_flat, magic_pen_pct), attack speed stats (base_AS, AS_ratio, AS_growth, bonus_AS, windup_pct, AS_cap), and `is_melee` flag. `level_up()` applies scaling formula `base * (0.65 + 0.035 * level)` and grants a skill point (level 1 starts with 1 SP). `total_attack_speed()` / `attack_interval()` / `windup_time()` compute AS using the LoL formula. `add_stats()` adds bonus stats, pen, and bonus AS from items/buffs.

- **`lol_champions/ability.py`** — `Ability` dataclass: tracks `name`, `max_level` (5 for Q/W/E, 3 for R), `current_level`.

- **`lol_champions/fiora.py`** — `Fiora(Champion)`: base stats (AS 0.69, windup 13.79%, AS cap 3.003), 4 `Ability` instances. Methods `Q()`, `W()`, `E()`, `passive()` return dicts with `raw_damage` and `damage_type` keys (compatible with `calculate_damage()`). `R()` has no `raw_damage` (damage comes from 4x passive procs). Timing constants: Q_CAST_TIME=0.25s, W_CAST_TIME=0.75s (W_HIT_TIME=0.50s), VITAL_RESPAWN_DELAY=2.25s, R_VITAL_APPEAR_DELAY=0.5s. E_BONUS_AS per rank for 2 empowered attacks. Ability stats stored as parallel lists indexed by `ability.current_level - 1`.

- **`lol_champions/target.py`** — `Target` dataclass: `max_hp`, `armor`, `mr`, `bonus_armor`, `bonus_mr`. Properties `base_armor`/`base_mr` computed. `Target.from_champion()` factory creates a target from any Champion instance.

- **`lol_champions/damage.py`** — Damage engine. `effective_resistance()` applies LoL penetration order: flat reduction → % reduction → % pen → flat pen (lethality). `damage_after_mitigation()` applies `dmg * 100/(100+R)`. `calculate_damage()` is the high-level function: reads `raw_damage`/`damage_type` from ability dict, applies pen from champion, mitigates against target, supports `damage_amp` for effects like PtA exposure.

- **`lol_champions/runes.py`** — 4 keystone rune dataclasses. Each has methods returning dicts. Rune procs that deal damage include `raw_damage`/`damage_type` keys so they work with `calculate_damage()`. Conqueror returns bonus AD/AP to add via `champion.add_stats()`.

- **`lol_champions/dps.py`** — DPS optimizer engine. Uses branch-and-bound DFS (<=10s) or greedy heuristic (>10s) to find optimal action sequence. `DPSState` tracks dual timers (ability_lock + AA cooldown), per-ability cooldowns, E two-attack model (e_autos_remaining: 0/1/2), R vitals, vital respawn (2.25s), and rune state. `DamageTable` pre-computes all damage values. Actions: AA, Q, W, E_ACTIVATE, E_FIRST, E_CRIT, R_ACTIVATE, WAIT. Hit-frame timing: damage lands at windup (AA/E), dash end (Q 0.25s), or mid-channel (W at 0.5s into 0.75s lockout). `optimize_dps()` is the public API.

## Key Patterns

- Ability/rune methods return dicts with `raw_damage` and `damage_type` keys — the contract for `calculate_damage()`.
- `damage_type` is one of: `"physical"`, `"magic"`, `"true"`, `"adaptive"` (resolved via bonus AD vs AP).
- All stat/ability data is hardcoded in lists sourced from the [LoL Wiki](https://wiki.leagueoflegends.com).
- Ability methods return `{"error": "message"}` when ability is not learned.
- Rune level scaling uses `_level_scale(min, max, level)` for linear interpolation over levels 1-18.

## Adding a New Champion

Subclass `Champion`, set base stats and scaling values, create 4 `Ability` instances, implement `Q()`/`W()`/`E()`/`R()`/`passive()` methods returning dicts with `raw_damage` and `damage_type` keys, and implement `level_ability()` with restrictions.
