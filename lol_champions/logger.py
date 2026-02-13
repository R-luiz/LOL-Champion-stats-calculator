"""Logging system for damage calculation results.

Saves detailed combo timelines to text files in a ``logs/`` directory.
Each log file captures champion state, target stats, item build,
rune, and the full per-action timeline with damage breakdowns.

Usage::

    from lol_champions.logger import log_result, log_build_results

    # Log a single optimize_dps result
    log_result(result, champion=fiora, target=target,
               items=["Trinity Force", "BotRK"], rune="PtA")

    # Log build optimizer top N results
    log_build_results(builds, champion=fiora, target=target, rune="PtA")
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"


def _ensure_log_dir():
    """Create the logs directory if it doesn't exist."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _champion_header(champion) -> str:
    """Format champion info as a header block."""
    lines = []
    name = type(champion).__name__
    lines.append(f"Champion: {name} Level {champion.level}")
    lines.append(f"  AD: {champion.total_AD:.1f}  AP: {champion.total_AP:.1f}  "
                 f"HP: {champion.total_HP:.1f}  AR: {champion.total_AR:.1f}  "
                 f"MR: {champion.total_MR:.1f}")
    lines.append(f"  AS: {champion.total_attack_speed():.3f}  "
                 f"Lethality: {champion.lethality:.1f}  "
                 f"Armor Pen %: {champion.armor_pen_pct:.0%}  "
                 f"Life Steal: {champion.life_steal:.0%}  "
                 f"Omnivamp: {champion.omnivamp:.0%}")
    # Abilities
    abilities = []
    for attr in ('q_ability', 'w_ability', 'e_ability', 'r_ability'):
        ab = getattr(champion, attr, None)
        if ab:
            abilities.append(f"{ab.name[0]}[{ab.current_level}]")
    if abilities:
        lines.append(f"  Abilities: {' '.join(abilities)}")
    return "\n".join(lines)


def _target_header(target) -> str:
    """Format target info."""
    return f"Target: HP={target.max_hp}  Armor={target.armor}  MR={target.mr}"


def _format_timeline(result: dict) -> str:
    """Format the full timeline as readable text."""
    lines = []
    lines.append("Timeline:")
    for e in result["timeline"]:
        notes = e["notes"] if e["notes"] else ""
        lines.append(f"  {e['time']:6.2f}s  {e['action']:12s}  "
                     f"dmg={e['damage']:>7.1f}  heal={e['healing']:>6.1f}  "
                     f"{notes}")
    return "\n".join(lines)


def _format_single_result(result: dict, items=None, rune=None) -> str:
    """Format a single optimize_dps result as a full log entry."""
    lines = []

    # Build header
    if items:
        if isinstance(items[0], str):
            build_str = " + ".join(items)
        else:
            build_str = " + ".join(type(i).__name__ for i in items)
    else:
        build_str = "(no items)"

    rune_str = ""
    if rune:
        if isinstance(rune, str):
            rune_str = rune
        else:
            rune_str = type(rune).__name__

    lines.append(f"{build_str}" + (f" — {rune_str}" if rune_str else ""))
    lines.append(f"Total: {result['total_damage']} dmg | "
                 f"{result['dps']} DPS | "
                 f"{result['total_healing']} heal")
    lines.append(f"Sequence: {result['sequence']}")
    lines.append("")
    lines.append(_format_timeline(result))

    return "\n".join(lines)


def log_result(
    result: dict,
    champion=None,
    target=None,
    items=None,
    rune=None,
    filename: str = None,
) -> str:
    """Log a single optimize_dps result to a file.

    Args:
        result: Dict returned by optimize_dps().
        champion: Champion instance (for header info).
        target: Target instance (for header info).
        items: Item names (list of str) or item instances.
        rune: Rune name (str) or rune instance.
        filename: Custom filename. Auto-generated if None.

    Returns:
        Path to the written log file.
    """
    _ensure_log_dir()

    if filename is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        if items:
            if isinstance(items[0], str):
                slug = "_".join(n.replace(" ", "").replace("'", "")[:10]
                                for n in items[:3])
            else:
                slug = "_".join(type(i).__name__[:10] for i in items[:3])
        else:
            slug = "no_items"
        filename = f"{ts}_{slug}.log"

    path = LOG_DIR / filename

    lines = []
    lines.append("=" * 70)
    lines.append(f"LOG: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)

    if champion:
        lines.append("")
        lines.append(_champion_header(champion))
    if target:
        lines.append(_target_header(target))

    lines.append("")
    lines.append("-" * 70)
    lines.append(_format_single_result(result, items=items, rune=rune))
    lines.append("-" * 70)
    lines.append("")

    with open(path, "w") as f:
        f.write("\n".join(lines))

    return str(path)


def log_build_results(
    builds: List[Dict[str, Any]],
    champion=None,
    target=None,
    rune=None,
    time_limit: float = 0.0,
    filename: str = None,
) -> str:
    """Log build optimizer results (top N builds) to a file.

    Args:
        builds: List of dicts returned by optimize_build().
        champion: Champion instance (for header info).
        target: Target instance (for header info).
        rune: Rune name or instance.
        time_limit: Combo duration used.
        filename: Custom filename. Auto-generated if None.

    Returns:
        Path to the written log file.
    """
    _ensure_log_dir()

    if filename is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        n_items = len(builds[0]["items"]) if builds else 0
        filename = f"{ts}_build_{n_items}items.log"

    path = LOG_DIR / filename

    rune_str = ""
    if rune:
        rune_str = rune if isinstance(rune, str) else type(rune).__name__

    lines = []
    lines.append("=" * 70)
    lines.append(f"BUILD OPTIMIZER LOG: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)

    if champion:
        lines.append("")
        lines.append(_champion_header(champion))
    if target:
        lines.append(_target_header(target))
    if time_limit > 0:
        lines.append(f"Time limit: {time_limit}s")
    if rune_str:
        lines.append(f"Rune: {rune_str}")

    lines.append("")
    lines.append("=" * 70)
    lines.append("RANKINGS")
    lines.append("=" * 70)

    for i, b in enumerate(builds, 1):
        names = " + ".join(b["items"])
        lines.append(f"  #{i:2d}: {names:50s}  {b['dps']:>7.1f} DPS  "
                     f"({b['total_damage']:>7.1f} dmg, {b['total_healing']:>6.1f} heal)")

    # Detailed timeline for each build
    for i, b in enumerate(builds, 1):
        lines.append("")
        lines.append("=" * 70)
        lines.append(f"#{i} DETAIL")
        lines.append("=" * 70)
        lines.append(_format_single_result(b, items=b["items"], rune=rune))

    lines.append("")

    with open(path, "w") as f:
        f.write("\n".join(lines))

    return str(path)
