"""Quick demo of the live display with simulated game data."""

import io
from contextlib import redirect_stdout

from lol_champions import Fiora, Target, optimize_dps
from lol_champions.runes import PressTheAttack
from lol_champions.items import SpearOfShojin
from live import _compute_damage, _build_modifiers, _display

# ─── Simulate level 14 Fiora with items ───
buf = io.StringIO()
with redirect_stdout(buf):
    fiora = Fiora()
    for _ in range(13):
        fiora.level_up()
    for _ in range(5):
        fiora.level_ability("Q")
    for _ in range(5):
        fiora.level_ability("E")
    fiora.level_ability("W")
    fiora.level_ability("R")
    fiora.level_ability("R")
    fiora.level_ability("R")

# Items:
#   Doran's Blade:    10 AD, 100 HP, 3.5% omnivamp
#   Ravenous Hydra:   65 AD, 25 AH, 10% life steal
#   Endless Hunger:   60 AD, 5% omnivamp
fiora.add_stats(
    bonus_AD=10 + 65 + 60,  # Doran + Hydra + Endless
    bonus_HP=100,            # Doran
)
fiora.life_steal = 0.10         # Hydra 10%
fiora.omnivamp = 0.035 + 0.05  # Doran 3.5% + Endless 5%
fiora.health_regen_per_sec = 14.2

current_hp = 1650.0
max_hp = fiora.total_HP
target = Target(max_hp=2800, armor=152, mr=58)

keystone_name = "pta"
keystone = PressTheAttack()
minor_runes = {"last_stand"}
items_list = []
item_names = ["Doran's Blade", "Ravenous Hydra", "Endless Hunger"]

# ─── Compute ───
mods = _build_modifiers(fiora, target, minor_runes, current_hp, max_hp)
damages = _compute_damage(fiora, target, mods, items_list, False, keystone_name, keystone)

buf2 = io.StringIO()
with redirect_stdout(buf2):
    dps_result = optimize_dps(
        champion=fiora, target=target, time_limit=5.0,
        rune=keystone, bonus_as=0, damage_modifiers=mods, items=items_list,
    )

buf3 = io.StringIO()
with redirect_stdout(buf3):
    full = optimize_dps(
        champion=fiora, target=target, time_limit=20.0,
        rune=keystone, bonus_as=0, damage_modifiers=mods, items=items_list,
    )

timeline = full.get("timeline", [])
cumulative = cumulative_heal = 0.0
kill_actions = []
kill_time = None
for step in timeline:
    cumulative += step.get("damage", 0)
    cumulative_heal += step.get("healing", 0)
    kill_actions.append(step["action"])
    if cumulative >= target.max_hp:
        kill_time = step["time"]
        break

kill_result = None
if kill_time is not None:
    kill_result = {
        "time": kill_time,
        "actions": kill_actions,
        "damage": round(cumulative, 1),
        "healing": round(cumulative_heal, 1),
    }

# ─── Display ───
_display(
    fiora, target, "Darius (Lv14, scaling + flat 65)",
    keystone_name, minor_runes,
    current_hp, max_hp, item_names, damages, 1245.0,
    dps_result, kill_result,
)
