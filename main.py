"""Damage calculation demo for the LoL Champion Simulator."""

from lol_champions import Fiora, Target, calculate_damage
from lol_champions.runes import PressTheAttack, Conqueror, HailOfBlades, GraspOfTheUndying


def fmt(result: dict) -> str:
    """Format a calculate_damage result into a readable one-liner."""
    return (f"{result['raw_damage']} {result['damage_type']} -> "
            f"{result['total_damage']} after mitigation "
            f"({result['damage_reduction_pct']}% reduced, "
            f"eff. resistance: {result['effective_resistance']})")


def main():
    print("=" * 70)
    print("FIORA DAMAGE CALCULATOR")
    print("=" * 70)

    # ─── Setup: Fiora level 9, Q rank 5, with items ───
    fiora = Fiora()
    for _ in range(8):
        fiora.level_up()
    # Max Q first (5 points), then W rank 1, E rank 1, R rank 1
    for _ in range(5):
        fiora.level_ability('Q')
    fiora.level_ability('W')
    fiora.level_ability('E')
    fiora.level_ability('R')  # unlocked at level 6

    # Items: 50 bonus AD, 10 lethality
    fiora.add_stats(bonus_AD=50, lethality=10)

    print(f"\n{fiora}")
    print(f"Lethality: {fiora.lethality}  |  Armor Pen %: {fiora.armor_pen_pct}")

    # ─── Target: 80 armor, 50 MR, 2000 HP ───
    target = Target(armor=80, mr=50, max_hp=2000)
    print(f"\n{target}")

    # ─── Q damage (physical, mitigated by armor) ───
    print("\n" + "-" * 70)
    print("Q - LUNGE (physical damage vs armor)")
    print("-" * 70)
    q_data = fiora.Q()
    q_result = calculate_damage(q_data, target, champion=fiora)
    print(f"  {fmt(q_result)}")

    # ─── Passive (true damage, bypasses everything) ───
    print("\n" + "-" * 70)
    print("PASSIVE - DUELIST'S DANCE (true damage, ignores armor)")
    print("-" * 70)
    passive_data = fiora.passive(target_max_hp=target.max_hp)
    passive_result = calculate_damage(passive_data, target, champion=fiora)
    print(f"  {fmt(passive_result)}")
    print(f"  Heal: {passive_data['heal']}")

    # ─── W damage (magic, mitigated by MR) ───
    print("\n" + "-" * 70)
    print("W - RIPOSTE (magic damage vs MR)")
    print("-" * 70)
    w_data = fiora.W()
    w_result = calculate_damage(w_data, target, champion=fiora)
    print(f"  {fmt(w_result)}")

    # ─── E empowered auto (physical crit) ───
    print("\n" + "-" * 70)
    print("E - BLADEWORK (crit-empowered auto vs armor)")
    print("-" * 70)
    e_data = fiora.E()
    e_result = calculate_damage(e_data, target, champion=fiora)
    print(f"  {fmt(e_result)}")
    print(f"  Crit multiplier: {e_data['critical_damage']}")

    # ═══════════════════════════════════════════════════════════════════
    # RUNES
    # ═══════════════════════════════════════════════════════════════════

    # ─── Press the Attack ───
    print("\n" + "=" * 70)
    print("RUNE: PRESS THE ATTACK")
    print("=" * 70)
    pta = PressTheAttack()
    pta_proc = pta.proc_damage(fiora.level, fiora.bonus_AD, fiora.bonus_AP)
    pta_result = calculate_damage(pta_proc, target, champion=fiora)
    print(f"  Proc:        {fmt(pta_result)}")

    # Q damage with PtA exposure active (8% amp)
    exposure = pta.exposure()
    q_exposed = calculate_damage(q_data, target, champion=fiora,
                                 damage_amp=exposure["damage_amp"])
    print(f"  Q + exposed: {fmt(q_exposed)}")

    # ─── Conqueror ───
    print("\n" + "=" * 70)
    print("RUNE: CONQUEROR (12 stacks)")
    print("=" * 70)
    conq = Conqueror()
    conq_bonus = conq.stat_bonus(fiora.level, stacks=12, adaptive="ad")
    print(f"  Bonus AD at max stacks: +{conq_bonus['bonus_AD']}")

    # Temporarily add conqueror bonus AD
    fiora.add_stats(bonus_AD=conq_bonus["bonus_AD"])
    q_with_conq = calculate_damage(fiora.Q(), target, champion=fiora)
    print(f"  Q + Conqueror: {fmt(q_with_conq)}")
    conq_heal = conq.healing(q_with_conq["post_mitigation_damage"], is_melee=True)
    print(f"  Conqueror heal from Q: {conq_heal['heal']} ({conq_heal['heal_pct']} of post-mitigation)")
    # Remove conqueror bonus
    fiora.add_stats(bonus_AD=-conq_bonus["bonus_AD"])

    # ─── Hail of Blades ───
    print("\n" + "=" * 70)
    print("RUNE: HAIL OF BLADES")
    print("=" * 70)
    hob = HailOfBlades()
    hob_data = hob.attack_speed_bonus(is_melee=True)
    print(f"  {hob_data['description']}")
    print(f"  Cooldown: {hob_data['cooldown']}s")

    # ─── Grasp of the Undying ───
    print("\n" + "=" * 70)
    print("RUNE: GRASP OF THE UNDYING")
    print("=" * 70)
    grasp = GraspOfTheUndying()
    grasp_proc = grasp.proc_damage(fiora.total_HP, is_melee=True)
    grasp_result = calculate_damage(grasp_proc, target, champion=fiora)
    print(f"  Proc:         {fmt(grasp_result)}")
    grasp_heal = grasp.healing(fiora.total_HP, is_melee=True)
    print(f"  Heal: {grasp_heal['heal']} ({grasp_heal['hp_pct']} of max HP)")
    grasp_perm = grasp.permanent_hp(is_melee=True)
    print(f"  Permanent HP: +{grasp_perm['permanent_hp']}")

    # ═══════════════════════════════════════════════════════════════════
    # CHAMPION VS CHAMPION
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("CHAMPION VS CHAMPION: Fiora Q vs Level 11 Fiora with +40 armor")
    print("=" * 70)
    enemy = Fiora()
    for _ in range(10):
        enemy.level_up()
    enemy.add_stats(bonus_AR=40)
    enemy_target = Target.from_champion(enemy)
    print(f"  {enemy_target}")
    q_vs_enemy = calculate_damage(fiora.Q(), enemy_target, champion=fiora)
    print(f"  Q damage: {fmt(q_vs_enemy)}")

    print("\n" + "=" * 70)
    print("Done!")


if __name__ == "__main__":
    main()
