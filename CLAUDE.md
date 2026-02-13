# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

League of Legends Champion Simulator (v1.6.0) with damage calculation engine. Models champion mechanics, stats, abilities, runes, items, and computes post-mitigation damage against targets. Includes a DPS optimizer (branch-and-bound search), build optimizer (exhaustive/greedy over item combos), and real-time live client integration. Currently implements Fiora. Pure Python, no external dependencies.

## Commands

```bash
python main.py                          # Full feature demo (abilities, runes, items, DPS, builds)
python cli.py --help                    # JSON CLI for AI assistants (all flags documented)
python cli.py --level 9 --q 5 --bonus-ad 50 --target-armor 80  # Single ability calc
python cli.py --time 5 --level 9 ...   # DPS optimizer mode
python live.py                          # Real-time dashboard (requires running LoL game)
python live.py --target Darius --time 5 # Live + DPS optimizer
python demo_live.py                     # Simulated live dashboard (no game needed)
```

No build step, test framework, or linter is configured. Validation: `validate_catalog()` compares hardcoded item stats against Data Dragon CDN to detect patch drift.

## Architecture

```
Champion (dataclass, base class) ──→ Fiora (subclass, concrete champion)
    uses ──→ Ability (dataclass, tracks level/max_level per ability slot)

Target (dataclass) ── damage target with HP/armor/MR
    Target.from_champion() ── use a Champion as target

calculate_damage(ability_data, target, champion, damage_modifiers, ...) ── core damage pipeline
    uses ──→ effective_resistance() ── penetration order: flat reduction → % reduction → % pen → lethality
    uses ──→ damage_after_mitigation() ── LoL formula: dmg × 100/(100+R)
    applies ──→ damage_modifiers multiplicatively: Π(1 + mod.amp)

optimize_dps(champion, target, time_limit, rune, items, ...) ── DPS optimizer
    uses ──→ DamageTable (pre-computed damage for all actions under each rune condition)
    uses ──→ DPSState (timers, cooldowns, vital respawn, rune/item state)
    branch-and-bound DFS (≤10s) or greedy heuristic (>10s)

optimize_build(champion, target, time_limit, item_count, pool, ...) ── build optimizer
    exhaustive search (≤3 items) or greedy iterative (>3 items)
    enforces exclusive groups: spellblade (max 1), hydra (max 1), immolate (max 1)
    uses ──→ ITEM_CATALOG (29 items with stats, proc classes, exclusive groups)
```

### Key Files

- **`lol_champions/champion.py`** — Base `Champion` dataclass: 5 core stats (AD, AP, HP, AR, MR) each with base/scaling/bonus/total fields, plus penetration stats, attack speed stats (base_AS, AS_ratio, AS_growth, bonus_AS, windup_pct, AS_cap), sustain stats (life_steal, omnivamp, health_regen_per_sec), and `is_melee` flag. `level_up()` applies scaling formula `base * (0.65 + 0.035 * level)`. `add_stats()` adds bonus stats from items/buffs.

- **`lol_champions/fiora.py`** — `Fiora(Champion)`: base stats (AS 0.69, windup 13.79%, AS cap 3.003), 4 `Ability` instances. Methods `Q()`, `W()`, `E()`, `passive()` return dicts with `raw_damage` and `damage_type` keys. `R()` has no `raw_damage` (damage comes from 4x passive procs). Timing constants: Q_CAST_TIME=0.25s, W_CAST_TIME=0.75s (W_HIT_TIME=0.50s), VITAL_RESPAWN_DELAY=2.25s, R_VITAL_APPEAR_DELAY=0.5s. E_BONUS_AS per rank for 2 empowered attacks.

- **`lol_champions/damage.py`** — Damage engine. `calculate_damage()` reads `raw_damage`/`damage_type` from ability dict, applies pen, mitigates, supports `damage_amp` and `damage_modifiers`. `calculate_combo()` tracks Shojin stacks and rune state per step.

- **`lol_champions/items.py`** — 29 item dataclasses organized by category: on-hit (BotRK, Wit's End, Nashor's, Terminus, Titanic Hydra), stacking on-hit (Kraken Slayer), spellblade (Trinity Force, Iceborn, Lich Bane), energized (Voltaic, RFC, Shiv, Stormrazor), amplifiers (LDR), actives (Hydras, Stridebreaker), burn/immolate (Liandry's, Sunfire, Hollow Radiance), conditional (Sundered Sky, Dead Man's). Action sets defined: `ON_HIT_ACTIONS`, `ABILITY_CAST_ACTIONS`, `ABILITY_DAMAGE_ACTIONS`.

- **`lol_champions/dps.py`** — DPS optimizer. `DPSState` tracks dual timers (ability_lock + AA cooldown), per-ability cooldowns, E two-attack model (e_autos_remaining: 0/1/2), R vitals, vital respawn, rune state, and all item states (Shojin stacks, spellblade armed, energized stacks, Kraken hits, BotRK target HP tracking). Actions: AA, Q, W, E_ACTIVATE, E_FIRST, E_CRIT, R_ACTIVATE, WAIT, HYDRA_ACTIVE, STRIDEBREAKER. `DamageTable` pre-computes damage with static amps baked in; Shojin/BotRK applied dynamically.

- **`lol_champions/build_optimizer.py`** — Build optimizer. `ITEM_CATALOG` maps item names to `{id, stats, proc_class, exclusive_groups}`. `_apply_build()`/`_undo_build()` temporarily modify champion stats. Exhaustive for ≤3 items, greedy for 4-6.

- **`lol_champions/runes.py`** — 4 keystones (PressTheAttack, Conqueror, HailOfBlades, GraspOfTheUndying) + 3 minor runes (LastStand, CoupDeGrace, CutDown). Keystones return `{raw_damage, damage_type}` dicts. Minor runes expose `damage_amp()` returning a decimal.

- **`lol_champions/live_client.py`** — Riot Live Client Data API wrapper (polls `127.0.0.1:2999`).

- **`lol_champions/data_dragon.py`** — Data Dragon CDN fetcher with local file cache (`~/.cache/lol_data/<version>/`).

- **`lol_champions/logger.py`** — Calculation logging to `logs/` directory with rankings tables and per-action timelines.

- **`cli.py`** — JSON CLI for AI assistants. Suppresses champion print output, returns structured JSON.

- **`live.py`** — Real-time terminal dashboard. Polls Live Client API every 2s, estimates enemy stats, includes HP shard calibration.

## Key Patterns

- **Ability contract**: Ability/rune/item proc methods return dicts with `raw_damage` and `damage_type` keys — the universal contract for `calculate_damage()`. `damage_type` is one of: `"physical"`, `"magic"`, `"true"`, `"adaptive"`.
- **Damage modifiers**: List of `{"name": str, "amp": float}` dicts. All amps stack multiplicatively: `total = post_mitigation × (1+damage_amp) × Π(1+mod.amp)`. Static amps (Last Stand, CoupDeGrace, CutDown) baked into DamageTable; Shojin applied dynamically per-action.
- **Error handling**: Ability methods return `{"error": "message"}` when ability is not learned.
- **Stat management**: `champion.add_stats()` is additive (call with negatives to undo). Build optimizer uses `_apply_build()`/`_undo_build()` pairs around each evaluation.
- **DPS timing model**: Damage lands at windup (AA/E), dash end (Q 0.25s), or mid-channel (W at 0.5s). E splits into 3 phases: E_ACTIVATE (instant AA reset), E_FIRST (regular AA), E_CRIT (guaranteed crit). Vital respawn delay is 2.25s; WAIT action lets search compare "ability now without vital" vs "wait for vital".
- **Item exclusivity**: Spellblade, Hydra, and Immolate groups are mutually exclusive (max 1 per group). Build optimizer enforces this via `_is_valid_combo()`.
- All stat/ability data is hardcoded in lists sourced from the [LoL Wiki](https://wiki.leagueoflegends.com).

## Adding a New Champion

Subclass `Champion`, set base stats and scaling values, create 4 `Ability` instances, implement `Q()`/`W()`/`E()`/`R()`/`passive()` methods returning dicts with `raw_damage` and `damage_type` keys, and implement `level_ability()` with ultimate restrictions (levels 6/11/16).
