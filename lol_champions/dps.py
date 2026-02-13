"""DPS optimizer engine using branch-and-bound search.

Finds the action sequence that maximizes damage in a given time window,
accounting for attack speed, ability cooldowns, animation times,
Fiora vital procs, and rune interactions.

All timing values sourced from https://wiki.leagueoflegends.com/en-us/

Timing model:
  - AA damage lands after windup (attack_interval * windup_pct)
  - Q damage lands at end of dash (Q_CAST_TIME)
  - W damage lands mid-channel (W_HIT_TIME, stab fires at 0.5s of 0.75s lockout)
  - E empowers NEXT TWO autos: E_FIRST (regular AA) then E_CRIT (guaranteed crit)
  - E bonus AS only applies for those 2 empowered attacks
  - R_ACTIVATE reveals 4 vitals after 0.5s delay
  - Vital respawn: 2.25s after proc (0.5s identify + 1.75s targetable)
"""

import copy
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple

from .damage import calculate_damage


# Actions that count as on-hit (trigger PtA stacks, Grasp proc)
ON_HIT_ACTIONS = {"AA", "Q", "E_FIRST", "E_CRIT"}


# ─── STATE ───


@dataclass
class DPSState:
    """Simulation state for the DPS search.

    Two timers govern when the champion can act:
      ability_lock_until - animation lock, nothing can happen until this clears
      next_aa_at         - auto-attack cooldown (separate from animation lock)
    """
    time: float = 0.0
    ability_lock_until: float = 0.0
    next_aa_at: float = 0.0
    q_cd_until: float = 0.0
    w_cd_until: float = 0.0
    e_cd_until: float = 0.0
    r_cd_until: float = 0.0
    # E state: empowers next 2 autos (E_FIRST then E_CRIT)
    e_autos_remaining: int = 0  # 2=E_FIRST pending, 1=E_CRIT pending, 0=inactive
    e_expires_at: float = 0.0   # E effect expires after 4s if not consumed
    # Vital state
    next_vital_at: float = 0.0
    r_vitals_remaining: int = 0
    # Rune state
    pta_hits: int = 0
    pta_exposed: bool = False
    conq_stacks: int = 0
    hob_stacks: int = 0
    hob_active_until: float = 0.0
    grasp_available: bool = True
    # Item state
    shojin_stacks: int = 0
    shojin_max_stacks: int = 0  # 0 = no Shojin
    # Accumulated results
    damage_so_far: float = 0.0
    healing_so_far: float = 0.0
    actions: list = field(default_factory=list)

    def copy(self) -> 'DPSState':
        new = copy.copy(self)
        new.actions = list(self.actions)
        return new


# ─── PRE-COMPUTED DAMAGE TABLE ───


@dataclass
class DamageTable:
    """Pre-computed damage values for every action under each rune condition."""
    aa: float = 0.0
    aa_pta: float = 0.0
    aa_conq: float = 0.0
    q: float = 0.0
    q_pta: float = 0.0
    q_conq: float = 0.0
    w: float = 0.0
    w_pta: float = 0.0
    w_conq: float = 0.0
    e_crit: float = 0.0
    e_crit_pta: float = 0.0
    e_crit_conq: float = 0.0
    passive: float = 0.0
    passive_pta: float = 0.0
    passive_conq: float = 0.0
    passive_heal: float = 0.0
    passive_heal_conq: float = 0.0
    pta_proc: float = 0.0
    grasp_proc: float = 0.0
    grasp_heal: float = 0.0
    q_cd: float = float('inf')
    w_cd: float = float('inf')
    e_cd: float = float('inf')
    r_cd: float = float('inf')
    # Static damage amplifier (Last Stand, Coup de Grace, etc.)
    # Pre-multiplied into table values. Stored for reporting.
    static_amp_multiplier: float = 1.0
    # Shojin per-stack amp (applied dynamically per-action)
    shojin_amp_per_stack: float = 0.0


def build_damage_table(
    champion, target, rune=None,
    damage_modifiers=None, items=None,
) -> DamageTable:
    """Pre-compute all damage values for the search.

    Static damage_modifiers (Last Stand, etc.) are baked into every
    table entry.  Shojin is stored as per-stack amp and applied
    dynamically at lookup time.
    """
    from .runes import PressTheAttack, Conqueror, GraspOfTheUndying
    from .items import SpearOfShojin

    table = DamageTable()

    # Compute static multiplier from damage_modifiers
    static_mult = 1.0
    for mod in (damage_modifiers or []):
        static_mult *= (1.0 + mod.get("amp", 0.0))
    table.static_amp_multiplier = round(static_mult, 4)

    # Shojin per-stack amp (for dynamic application)
    if items:
        for item in items:
            if isinstance(item, SpearOfShojin):
                table.shojin_amp_per_stack = item.amp_per_stack

    # Helper to apply static multiplier
    def _amp(val: float) -> float:
        return round(val * static_mult, 2)

    # Base damages (with static amp baked in)
    aa_data = champion.auto_attack()
    table.aa = _amp(calculate_damage(aa_data, target, champion=champion)["total_damage"])

    q_data = champion.Q()
    if "error" not in q_data:
        table.q = _amp(calculate_damage(q_data, target, champion=champion)["total_damage"])
        table.q_cd = q_data["cooldown"]

    w_data = champion.W()
    if "error" not in w_data:
        table.w = _amp(calculate_damage(w_data, target, champion=champion)["total_damage"])
        table.w_cd = w_data["cooldown"]

    e_data = champion.E()
    if "error" not in e_data:
        table.e_crit = _amp(calculate_damage(e_data, target, champion=champion)["total_damage"])
        table.e_cd = e_data["cooldown"]

    passive_data = champion.passive(target_max_hp=target.max_hp)
    table.passive = _amp(calculate_damage(passive_data, target, champion=champion)["total_damage"])
    table.passive_heal = passive_data.get("heal", 0.0)

    # R cooldown
    r_data = champion.R()
    if "error" not in r_data:
        table.r_cd = r_data["cooldown"]

    # PtA variants (8% amp on ALL damage types including true damage from vitals)
    if rune and isinstance(rune, PressTheAttack):
        table.aa_pta = _amp(calculate_damage(aa_data, target, champion=champion, damage_amp=0.08)["total_damage"])
        if "error" not in q_data:
            table.q_pta = _amp(calculate_damage(q_data, target, champion=champion, damage_amp=0.08)["total_damage"])
        if "error" not in w_data:
            table.w_pta = _amp(calculate_damage(w_data, target, champion=champion, damage_amp=0.08)["total_damage"])
        if "error" not in e_data:
            table.e_crit_pta = _amp(calculate_damage(e_data, target, champion=champion, damage_amp=0.08)["total_damage"])
        table.passive_pta = _amp(calculate_damage(passive_data, target, champion=champion, damage_amp=0.08)["total_damage"])
        proc = rune.proc_damage(champion.level, champion.bonus_AD, champion.bonus_AP)
        table.pta_proc = _amp(calculate_damage(proc, target, champion=champion)["total_damage"])

    # Conqueror variants (bonus AD at max stacks affects ability damage AND passive scaling)
    if rune and isinstance(rune, Conqueror):
        bonus = rune.stat_bonus(champion.level, stacks=rune.max_stacks, adaptive="ad")
        conq_ad = bonus["bonus_AD"]
        champion.add_stats(bonus_AD=conq_ad)
        try:
            table.aa_conq = _amp(calculate_damage(champion.auto_attack(), target, champion=champion)["total_damage"])
            cq = champion.Q()
            if "error" not in cq:
                table.q_conq = _amp(calculate_damage(cq, target, champion=champion)["total_damage"])
            cw = champion.W()
            if "error" not in cw:
                table.w_conq = _amp(calculate_damage(cw, target, champion=champion)["total_damage"])
            ce = champion.E()
            if "error" not in ce:
                table.e_crit_conq = _amp(calculate_damage(ce, target, champion=champion)["total_damage"])
            # Passive scales with bonus AD: 3% + 4% per 100 bonus AD
            conq_passive = champion.passive(target_max_hp=target.max_hp)
            table.passive_conq = _amp(calculate_damage(conq_passive, target, champion=champion)["total_damage"])
            table.passive_heal_conq = conq_passive.get("heal", 0.0)
        finally:
            champion.add_stats(bonus_AD=-conq_ad)

    # Grasp proc
    if rune and isinstance(rune, GraspOfTheUndying):
        proc = rune.proc_damage(champion.total_HP, is_melee=champion.is_melee)
        table.grasp_proc = _amp(calculate_damage(proc, target, champion=champion)["total_damage"])
        heal = rune.healing(champion.total_HP, is_melee=champion.is_melee)
        table.grasp_heal = heal["heal"]

    return table


# ─── ACTION RESOLUTION ───


def _rune_variant(state: DPSState, rune) -> str:
    """Return which rune damage variant to use: 'base', 'pta', or 'conq'."""
    from .runes import PressTheAttack, Conqueror
    if rune and isinstance(rune, Conqueror) and state.conq_stacks >= 12:
        return "conq"
    if rune and isinstance(rune, PressTheAttack) and state.pta_exposed:
        return "pta"
    return "base"


def _get_action_damage(action: str, table: DamageTable, state: DPSState, rune) -> float:
    """Look up pre-computed damage for an action given current rune state.

    Applies Shojin dynamic amp on top for ability/proc actions.
    """
    variant = _rune_variant(state, rune)

    lookup = {
        "AA":      (table.aa, table.aa_pta, table.aa_conq),
        "E_FIRST": (table.aa, table.aa_pta, table.aa_conq),  # Same damage as regular AA
        "Q":       (table.q, table.q_pta, table.q_conq),
        "W":       (table.w, table.w_pta, table.w_conq),
        "E_CRIT":  (table.e_crit, table.e_crit_pta, table.e_crit_conq),
    }
    if action not in lookup:
        return 0.0

    base, pta, conq = lookup[action]
    if variant == "conq":
        dmg = conq
    elif variant == "pta":
        dmg = pta
    else:
        dmg = base

    # Apply dynamic Shojin amp for ability/proc actions
    if table.shojin_amp_per_stack > 0 and action in ("Q", "W", "E_FIRST", "E_CRIT"):
        shojin_amp = state.shojin_stacks * table.shojin_amp_per_stack
        dmg = round(dmg * (1.0 + shojin_amp), 2)

    return dmg


def _get_vital_damage(table: DamageTable, state: DPSState, rune) -> Tuple[float, float]:
    """Return (vital_damage, vital_heal) for the current rune state.

    Shojin amp applies to vital (proc) damage.
    """
    variant = _rune_variant(state, rune)
    if variant == "conq":
        dmg, heal = table.passive_conq, table.passive_heal_conq
    elif variant == "pta":
        dmg, heal = table.passive_pta, table.passive_heal
    else:
        dmg, heal = table.passive, table.passive_heal

    # Shojin amplifies proc damage (vitals)
    if table.shojin_amp_per_stack > 0:
        shojin_amp = state.shojin_stacks * table.shojin_amp_per_stack
        dmg = round(dmg * (1.0 + shojin_amp), 2)

    return dmg, heal


def _available_actions(state: DPSState, table: DamageTable, time_limit: float) -> List[str]:
    """Return list of actions available at the current state time."""
    t = state.time
    if t >= time_limit:
        return []

    if state.ability_lock_until > t:
        return ["WAIT"]

    actions = []

    # Check if E effect is still active (2 empowered autos within 4s window)
    e_active = state.e_autos_remaining > 0 and state.e_expires_at > t

    # AA / E_FIRST / E_CRIT (mutually exclusive for the AA slot)
    if state.next_aa_at <= t:
        if e_active and state.e_autos_remaining == 2:
            actions.append("E_FIRST")
        elif e_active and state.e_autos_remaining == 1:
            actions.append("E_CRIT")
        else:
            actions.append("AA")

    # Q
    if table.q_cd < float('inf') and state.q_cd_until <= t:
        actions.append("Q")

    # W
    if table.w_cd < float('inf') and state.w_cd_until <= t:
        actions.append("W")

    # E activation (only when E is not already active and off cooldown)
    if table.e_cd < float('inf') and state.e_cd_until <= t and not e_active:
        actions.append("E_ACTIVATE")

    # R activation (only when R is learned, off cooldown, and no active R vitals)
    if table.r_cd < float('inf') and state.r_cd_until <= t and state.r_vitals_remaining == 0:
        actions.append("R_ACTIVATE")

    if not actions:
        actions.append("WAIT")
    elif state.next_vital_at > t and state.next_vital_at < time_limit:
        # A vital is about to respawn — offer WAIT so the search can
        # compare "use ability now without vital" vs "wait for vital
        # then use ability with vital proc (damage + heal + MS)".
        # In short burst windows where no vital will respawn before
        # time_limit, this branch is never taken, preserving burst.
        actions.append("WAIT")

    return actions


def _get_extra_as(state: DPSState, champion, rune) -> float:
    """Get current extra bonus AS% from E and HoB."""
    extra = 0.0
    # E bonus AS only active while empowered autos remain (not a flat 4s buff)
    e_active = state.e_autos_remaining > 0 and state.e_expires_at > state.time
    if e_active and hasattr(champion, 'e_bonus_attack_speed'):
        extra += champion.e_bonus_attack_speed()
    if rune and state.hob_stacks > 0 and state.hob_active_until > state.time:
        from .runes import HailOfBlades
        if isinstance(rune, HailOfBlades):
            hob_data = rune.attack_speed_bonus(is_melee=champion.is_melee)
            extra += hob_data["bonus_attack_speed_value"]
    return extra


def _apply_action(
    state: DPSState,
    action: str,
    table: DamageTable,
    champion,
    rune,
    time_limit: float,
) -> DPSState:
    """Apply an action to the current state, returning a new state."""
    from .runes import PressTheAttack, Conqueror, HailOfBlades, GraspOfTheUndying

    s = state.copy()
    t = s.time

    extra_as = _get_extra_as(s, champion, rune)
    atk_interval = champion.attack_interval(extra_bonus_as_pct=extra_as)
    wnd_time = champion.windup_time(extra_bonus_as_pct=extra_as)

    # ─── WAIT ───
    if action == "WAIT":
        events = [time_limit]
        if s.ability_lock_until > t:
            events.append(s.ability_lock_until)
        if s.next_aa_at > t:
            events.append(s.next_aa_at)
        for cd in [s.q_cd_until, s.w_cd_until, s.e_cd_until]:
            if cd > t:
                events.append(cd)
        if s.next_vital_at > t:
            events.append(s.next_vital_at)
        s.time = min(events)
        return s

    # ─── R_ACTIVATE (instant, no damage) ───
    if action == "R_ACTIVATE":
        s.ability_lock_until = t  # instant cast
        s.r_vitals_remaining = 4
        s.r_cd_until = t + table.r_cd
        # R vitals appear 0.5s after cast; overrides normal vital timer
        s.next_vital_at = t + champion.R_VITAL_APPEAR_DELAY
        s.actions.append((t, "R_ACTIVATE", 0.0, ["instant", "4-vitals"], 0.0))
        return s

    # ─── E_ACTIVATE (instant, no damage, resets AA timer) ───
    if action == "E_ACTIVATE":
        s.ability_lock_until = t
        s.next_aa_at = t  # AA reset
        s.e_autos_remaining = 2
        s.e_expires_at = t + 4.0
        s.e_cd_until = t + table.e_cd
        s.actions.append((t, "E_ACTIVATE", 0.0, ["instant", "AA-reset"], 0.0))
        return s

    # ─── DAMAGING ACTIONS ───
    heal_before = s.healing_so_far
    damage = 0.0
    hit_time = t  # when damage actually lands (after windup/cast)
    notes = []
    is_on_hit = action in ON_HIT_ACTIONS

    # Shojin: stack is granted AFTER damage (triggering ability does NOT
    # benefit from its own stack).  We record pre-damage stacks, then
    # increment after all damage lookups for this action.
    shojin_granted = False

    if action == "AA":
        hit_time = t + wnd_time
        damage = _get_action_damage("AA", table, s, rune)
        s.ability_lock_until = t + wnd_time
        s.next_aa_at = t + atk_interval

    elif action == "E_FIRST":
        # First empowered auto: regular AA damage, no crit, applies slow
        hit_time = t + wnd_time
        damage = _get_action_damage("E_FIRST", table, s, rune)
        s.ability_lock_until = t + wnd_time
        s.next_aa_at = t + atk_interval
        s.e_autos_remaining = 1
        notes.append("E-first")

    elif action == "E_CRIT":
        # Second empowered auto: guaranteed crit with modified damage
        hit_time = t + wnd_time
        damage = _get_action_damage("E_CRIT", table, s, rune)
        s.ability_lock_until = t + wnd_time
        s.next_aa_at = t + atk_interval
        s.e_autos_remaining = 0
        notes.append("E-crit")

    elif action == "Q":
        # Damage lands at end of dash
        hit_time = t + champion.Q_CAST_TIME
        damage = _get_action_damage("Q", table, s, rune)
        s.ability_lock_until = t + champion.Q_CAST_TIME
        s.next_aa_at = t + champion.Q_CAST_TIME  # AA reset
        s.q_cd_until = t + table.q_cd
        notes.append("AA-reset")

    elif action == "W":
        # Stab fires mid-channel (W_HIT_TIME), lockout for full W_CAST_TIME
        hit_time = t + getattr(champion, 'W_HIT_TIME', champion.W_CAST_TIME)
        damage = _get_action_damage("W", table, s, rune)
        s.ability_lock_until = t + champion.W_CAST_TIME
        s.w_cd_until = t + table.w_cd

    # ─── VITAL PROC (uses hit_time for when damage actually lands) ───
    vital_damage = 0.0
    if action in ("AA", "E_FIRST", "E_CRIT", "Q", "W"):
        # Vital is available if next_vital_at <= hit_time
        # Works for both R vitals (next_vital_at set to R appear time)
        # and normal vitals (next_vital_at set to respawn time)
        vital_available = s.next_vital_at <= hit_time

        if vital_available:
            vital_damage, vital_heal = _get_vital_damage(table, s, rune)
            s.healing_so_far += vital_heal
            notes.append(f"vital({round(vital_damage, 1)})")

            if s.r_vitals_remaining > 0:
                s.r_vitals_remaining -= 1
                if s.r_vitals_remaining == 0:
                    # All R vitals consumed → normal vital resumes
                    s.next_vital_at = hit_time + champion.VITAL_RESPAWN_DELAY
                # else: more R vitals available, next_vital_at stays (no delay between R vitals)
            else:
                s.next_vital_at = hit_time + champion.VITAL_RESPAWN_DELAY

    total_action_damage = damage + vital_damage

    # ─── PtA tracking ───
    if rune and isinstance(rune, PressTheAttack) and is_on_hit:
        s.pta_hits += 1
        if s.pta_hits == 3 and not s.pta_exposed:
            total_action_damage += table.pta_proc
            s.pta_exposed = True
            notes.append(f"PtA-proc({round(table.pta_proc, 1)})")

    # ─── Conqueror tracking (heals from ALL damage dealt: ability + vital) ───
    if rune and isinstance(rune, Conqueror) and action != "WAIT":
        s.conq_stacks = min(s.conq_stacks + 2, 12)
        if s.conq_stacks >= 12:
            heal_data = rune.healing(total_action_damage, is_melee=champion.is_melee)
            s.healing_so_far += heal_data["heal"]

    # ─── HoB tracking ───
    if rune and isinstance(rune, HailOfBlades) and is_on_hit:
        if s.hob_stacks == 0 and s.hob_active_until <= t:
            hob_data = rune.attack_speed_bonus(is_melee=champion.is_melee)
            s.hob_stacks = hob_data["initial_stacks"]
            s.hob_active_until = t + hob_data["duration"]
            notes.append("HoB-activated")
        elif s.hob_stacks > 0:
            s.hob_stacks -= 1

    # ─── Grasp tracking ───
    if rune and isinstance(rune, GraspOfTheUndying) and is_on_hit and s.grasp_available:
        total_action_damage += table.grasp_proc
        s.healing_so_far += table.grasp_heal
        s.grasp_available = False
        notes.append(f"Grasp({round(table.grasp_proc, 1)})")

    # ─── Shojin: grant stack AFTER damage is dealt ───
    if table.shojin_amp_per_stack > 0 and action in ("Q", "W", "E_FIRST", "E_CRIT"):
        s.shojin_stacks = min(s.shojin_stacks + 1, s.shojin_max_stacks)
        shojin_granted = True
        notes.append(f"Shojin({s.shojin_stacks})")

    # ─── Sustain healing (life steal + omnivamp) ───
    ls = getattr(champion, 'life_steal', 0.0)
    ov = getattr(champion, 'omnivamp', 0.0)
    sustain_heal = 0.0
    if is_on_hit and ls > 0 and damage > 0:
        sustain_heal += damage * ls          # LS on AA physical damage only
    if ov > 0 and total_action_damage > 0:
        sustain_heal += total_action_damage * ov  # omnivamp on ALL damage
    if sustain_heal > 0:
        s.healing_so_far += round(sustain_heal, 2)

    s.damage_so_far += total_action_damage
    action_heal = round(s.healing_so_far - heal_before, 2)
    s.actions.append((t, action, round(total_action_damage, 2), notes, action_heal))
    return s


# ─── SEARCH ───


def _upper_bound_dps(table: DamageTable, champion, extra_as: float = 0.0) -> float:
    """Loose upper bound on DPS for pruning."""
    min_interval = champion.attack_interval(extra_bonus_as_pct=extra_as)
    best_aa = max(table.aa, table.aa_conq, table.aa_pta, table.e_crit, table.e_crit_pta, table.e_crit_conq)
    aa_dps = best_aa / max(min_interval, 0.2)

    q_dps = 0.0
    if table.q_cd < float('inf'):
        q_dmg = max(table.q, table.q_conq, table.q_pta)
        q_dps = q_dmg / max(champion.Q_CAST_TIME, 0.1)

    base_dps = max(aa_dps, q_dps)
    best_passive = max(table.passive, table.passive_pta, table.passive_conq)
    # With R, vitals can proc every hit; without R, every 2.25s
    # Use fastest rate for loose upper bound
    vital_dps = best_passive / max(min_interval, 0.2) if best_passive > 0 else 0.0

    return base_dps + vital_dps


def _branch_and_bound(
    root: DPSState,
    table: DamageTable,
    champion,
    rune,
    time_limit: float,
) -> DPSState:
    """DFS branch-and-bound search over action sequences."""
    ub_dps = _upper_bound_dps(table, champion, extra_as=champion.bonus_AS)
    best = root.copy()
    stack = [root]
    nodes_explored = 0
    max_nodes = 500_000

    while stack and nodes_explored < max_nodes:
        state = stack.pop()
        nodes_explored += 1

        # Pruning
        remaining = time_limit - state.time
        if remaining > 0 and state.damage_so_far + remaining * ub_dps < best.damage_so_far:
            continue

        if state.time >= time_limit:
            if state.damage_so_far > best.damage_so_far:
                best = state
            continue

        actions = _available_actions(state, table, time_limit)

        for action in actions:
            new_state = _apply_action(state, action, table, champion, rune, time_limit)
            if new_state.damage_so_far > best.damage_so_far:
                best = new_state
            if new_state.time < time_limit:
                stack.append(new_state)

    return best


def _greedy_search(
    root: DPSState,
    table: DamageTable,
    champion,
    rune,
    time_limit: float,
) -> DPSState:
    """Greedy heuristic: pick the highest-damage available action at each step."""
    state = root

    while state.time < time_limit:
        actions = _available_actions(state, table, time_limit)

        if actions == ["WAIT"]:
            state = _apply_action(state, "WAIT", table, champion, rune, time_limit)
            continue

        best_action = None
        best_score = -1.0

        for action in actions:
            if action == "WAIT":
                # Score WAIT by the vital value it unlocks, discounted by
                # the time spent idling.  If vital respawns soon, the
                # damage + heal payoff is worth the wait.
                if state.next_vital_at > state.time and state.next_vital_at < time_limit:
                    wait_duration = state.next_vital_at - state.time
                    vital_dmg, vital_heal = _get_vital_damage(table, state, rune)
                    # Value = vital damage + heal value, penalised by wait
                    # as opportunity cost (lost AA DPS during idle time)
                    lost_dps = table.aa / max(champion.attack_interval(), 0.3)
                    score = (vital_dmg + vital_heal) - wait_duration * lost_dps
                else:
                    continue  # no vital to wait for
            elif action == "E_ACTIVATE":
                score = table.e_crit * 2  # prioritize enabling crit
            elif action == "R_ACTIVATE":
                # R gives 4 vitals; estimate value as ~3 extra vital procs
                vital_dmg, _ = _get_vital_damage(table, state, rune)
                score = vital_dmg * 3
            else:
                score = _get_action_damage(action, table, state, rune)
                # Add vital value if one will be available at hit time
                if state.next_vital_at <= state.time or state.r_vitals_remaining > 0:
                    vital_dmg, _ = _get_vital_damage(table, state, rune)
                    score += vital_dmg
            if score > best_score:
                best_score = score
                best_action = action

        if best_action is None:
            best_action = "WAIT"

        state = _apply_action(state, best_action, table, champion, rune, time_limit)

    return state


# ─── PUBLIC API ───


def _format_result(state: DPSState, time_limit: float, method: str) -> Dict[str, Any]:
    """Format a DPSState into the output dict."""
    timeline = []
    for entry in state.actions:
        t, action, damage, notes = entry[0], entry[1], entry[2], entry[3]
        healing = entry[4] if len(entry) > 4 else 0.0
        timeline.append({
            "time": round(t, 3),
            "action": action,
            "damage": damage,
            "healing": healing,
            "notes": ", ".join(notes) if notes else "",
        })

    sequence = " > ".join(entry[1] for entry in state.actions)
    dps = round(state.damage_so_far / time_limit, 2) if time_limit > 0 else 0.0

    return {
        "mode": "dps_optimize",
        "time_limit": time_limit,
        "method": method,
        "total_damage": round(state.damage_so_far, 2),
        "dps": dps,
        "total_healing": round(state.healing_so_far, 2),
        "action_count": len(state.actions),
        "timeline": timeline,
        "sequence": sequence,
    }


def optimize_dps(
    champion,
    target,
    time_limit: float,
    rune=None,
    r_active: bool = False,
    bonus_as: float = 0.0,
    damage_modifiers=None,
    items=None,
) -> Dict[str, Any]:
    """Find the action sequence that maximizes damage in time_limit seconds.

    Uses branch-and-bound DFS for time_limit <= 10s.
    Falls back to greedy heuristic for longer windows.

    Args:
        champion: Champion instance with AS fields and timing constants
        target: Target instance
        time_limit: Duration in seconds to optimize over
        rune: Optional keystone rune instance
        r_active: If True, R is pre-activated (4 vitals available immediately)
        bonus_as: Extra bonus attack speed % from items
        damage_modifiers: Static modifiers [{"name": str, "amp": float}, ...]
        items: Item instances with dynamic effects (e.g. SpearOfShojin)

    Returns:
        Dict with total_damage, dps, total_healing, timeline, sequence
    """
    if bonus_as > 0:
        champion.add_stats(bonus_AS=bonus_as)

    try:
        table = build_damage_table(
            champion, target, rune=rune,
            damage_modifiers=damage_modifiers, items=items,
        )

        root = DPSState()

        # Init Shojin state
        if items:
            from .items import SpearOfShojin
            for item in items:
                if isinstance(item, SpearOfShojin):
                    root.shojin_stacks = item.stacks
                    root.shojin_max_stacks = item.max_stacks

        if r_active:
            # R was already activated: 4 vitals available immediately, R on cooldown
            root.r_vitals_remaining = 4
            root.next_vital_at = 0.0
            root.r_cd_until = float('inf')
        else:
            # Normal start: one passive vital available at t=0
            root.next_vital_at = 0.0

        if time_limit <= 10.0:
            result_state = _branch_and_bound(root, table, champion, rune, time_limit)
            method = "branch_and_bound"
        else:
            result_state = _greedy_search(root, table, champion, rune, time_limit)
            method = "greedy"

        # Passive health regeneration over the fight
        hp_regen = getattr(champion, 'health_regen_per_sec', 0.0)
        if hp_regen > 0:
            result_state.healing_so_far += round(hp_regen * time_limit, 2)
    finally:
        if bonus_as > 0:
            champion.add_stats(bonus_AS=-bonus_as)

    return _format_result(result_state, time_limit, method)
