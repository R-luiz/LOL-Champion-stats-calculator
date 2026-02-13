"""Damage calculation demo for the LoL Champion Simulator."""

from lol_champions import Fiora, Target, calculate_damage, optimize_dps, optimize_build
from lol_champions.runes import PressTheAttack, Conqueror, HailOfBlades, GraspOfTheUndying
from lol_champions.items import (
    TrinityForce, BladeOfTheRuinedKing, WitsEnd, KrakenSlayer,
    SpearOfShojin, SunderedSky, LiandrysTorment,
)


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

    # ═══════════════════════════════════════════════════════════════════
    # ITEM DAMAGE PROCS
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("ITEM DAMAGE PROCS (vs 80 AR / 50 MR / 2000 HP target)")
    print("=" * 70)

    # Trinity Force Spellblade
    trinity = TrinityForce()
    proc = trinity.proc_damage(champion=fiora, target=target)
    result = calculate_damage(proc, target, champion=fiora)
    print(f"  Trinity Spellblade:  {fmt(result)}")

    # BotRK on-hit (9% current HP)
    botrk = BladeOfTheRuinedKing()
    proc = botrk.proc_damage(champion=fiora, target=target)
    result = calculate_damage(proc, target, champion=fiora)
    print(f"  BotRK on-hit:        {fmt(result)}")

    # Wit's End on-hit
    wits = WitsEnd()
    proc = wits.proc_damage(champion=fiora, target=target)
    result = calculate_damage(proc, target, champion=fiora)
    print(f"  Wit's End on-hit:    {fmt(result)}")

    # Kraken Slayer proc
    kraken = KrakenSlayer()
    proc = kraken.proc_damage(champion=fiora, target=target)
    result = calculate_damage(proc, target, champion=fiora)
    print(f"  Kraken Slayer 3rd:   {fmt(result)}")

    # Sundered Sky proc
    sky = SunderedSky()
    proc = sky.proc_damage(champion=fiora, target=target)
    result = calculate_damage(proc, target, champion=fiora)
    print(f"  Sundered Sky crit:   {fmt(result)}")

    # Liandry's burn (total over 3s)
    liandry = LiandrysTorment()
    burn = liandry.burn_damage(target=target)
    result = calculate_damage(burn, target, champion=fiora)
    print(f"  Liandry's burn (3s): {fmt(result)}")

    # ═══════════════════════════════════════════════════════════════════
    # DPS WITH ITEMS (Trinity + BotRK + Shojin, 5s)
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("DPS OPTIMIZER: Fiora Lv9 with Trinity + BotRK + Shojin (5s)")
    print("=" * 70)
    items_list = [TrinityForce(), BladeOfTheRuinedKing(), SpearOfShojin()]
    # Add item stats: Trinity (35 AD, 33% AS) + BotRK (40 AD, 25% AS)
    fiora.add_stats(bonus_AD=35 + 40, bonus_HP=300, bonus_AS=33 + 25)
    dps_result = optimize_dps(
        champion=fiora, target=target, time_limit=5.0,
        rune=PressTheAttack(), items=items_list,
    )
    print(f"  Total damage: {dps_result['total_damage']}")
    print(f"  DPS:          {dps_result['dps']}")
    print(f"  Healing:      {dps_result['total_healing']}")
    seq = dps_result['sequence']
    if len(seq) > 60:
        seq = seq[:57] + "..."
    print(f"  Sequence:     {seq}")
    # Undo item stats
    fiora.add_stats(bonus_AD=-(35 + 40), bonus_HP=-300, bonus_AS=-(33 + 25))

    # ═══════════════════════════════════════════════════════════════════
    # BUILD OPTIMIZER: Best 2-item build (exhaustive, fast demo)
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("BUILD OPTIMIZER: Best 2-item build for Fiora Lv9 (5s, vs 80 AR)")
    print("=" * 70)
    ad_pool = [
        "Trinity Force", "Blade of the Ruined King", "Spear of Shojin",
        "Kraken Slayer", "Wit's End", "Stridebreaker", "Sundered Sky",
        "Voltaic Cyclosword", "Profane Hydra", "Ravenous Hydra",
        "Titanic Hydra", "Lord Dominik's Regards", "Terminus",
    ]
    builds = optimize_build(
        champion=fiora, target=target, time_limit=5.0,
        item_count=2, rune=PressTheAttack(),
        pool=ad_pool, top_n=5,
    )
    for i, b in enumerate(builds, 1):
        names = " + ".join(b["items"])
        print(f"  #{i}: {names}  —  {b['dps']} DPS  "
              f"({b['total_damage']} dmg, {b['total_healing']} heal)")

    print("\n" + "=" * 70)
    print("Done!")


if __name__ == "__main__":
    main()
