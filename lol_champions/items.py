"""Item passive effects for League of Legends damage calculations.

Models item passives that act as damage multipliers.
Each item class exposes a ``damage_amp()`` method returning a decimal
amplifier (e.g. 0.03 = 3%), compatible with the ``damage_modifiers``
list accepted by ``calculate_damage()``.

All values sourced from https://leagueoflegends.fandom.com/wiki/
"""

from dataclasses import dataclass
from typing import Dict, Any


# ─── Actions that count as ability / proc damage for Spear of Shojin ───
# Basic auto-attacks (AA) do NOT benefit.  E_FIRST and E_CRIT count because
# they are empowered attacks granted by an ability (V14.5 change).
SHOJIN_AMPLIFIED_ACTIONS = {"Q", "W", "E", "E_FIRST", "E_CRIT", "PASSIVE"}

# Actions whose damage GRANTS a Shojin stack (ability casts, not passives).
# "Damage dealt by champion passives no longer incorrectly grant stacks." (V14.5)
SHOJIN_STACK_GRANTING_ACTIONS = {"Q", "W", "E", "E_FIRST", "E_CRIT"}


@dataclass
class SpearOfShojin:
    """Spear of Shojin — Focused Will passive.

    Stats: +45 AD, +450 HP, 25 basic ability haste.

    Passive — Focused Will:
        Dealing ability damage with a champion ability grants a stack
        for 6 seconds, stacking up to 4 times (1 per cast instance per
        second).  For each stack, ability damage and proc damage deal
        3% increased damage, up to 12% at 4 stacks.

    Important interactions:
        - Amplifies ALL damage types including true damage.
        - Does NOT amplify basic auto-attack damage.
        - Does NOT grant stacks from champion passive damage.
        - The triggering ability does NOT benefit from its own stack.
          (1st hit = 0 stacks amp, 2nd hit = 1 stack amp, etc.)
        - Empowered attacks from abilities (Fiora E) grant stacks and
          benefit from the amplification.

    Usage:
        shojin = SpearOfShojin(stacks=2)
        amp = shojin.damage_amp()        # -> 0.06 (6%)
        shojin.add_stack()               # stacks → 3
        shojin.is_amplified("Q")         # -> True
        shojin.is_amplified("AA")        # -> False
    """
    name: str = "Spear of Shojin"
    stacks: int = 0
    max_stacks: int = 4
    amp_per_stack: float = 0.03  # 3% per stack (same for melee and ranged)

    def damage_amp(self) -> float:
        """Current damage amplification based on stacks.

        Returns:
            Decimal amp (0.0–0.12).
        """
        return min(self.stacks, self.max_stacks) * self.amp_per_stack

    def add_stack(self) -> int:
        """Grant one Focused Will stack (capped at max_stacks).

        Returns:
            New stack count.
        """
        self.stacks = min(self.stacks + 1, self.max_stacks)
        return self.stacks

    def reset(self) -> None:
        """Reset stacks to 0."""
        self.stacks = 0

    @staticmethod
    def is_amplified(action: str) -> bool:
        """Whether *action* benefits from Focused Will amp.

        Args:
            action: Action name (e.g. "Q", "AA", "PASSIVE").

        Returns:
            True if the action's damage is amplified.
        """
        return action.upper() in SHOJIN_AMPLIFIED_ACTIONS

    @staticmethod
    def grants_stack(action: str) -> bool:
        """Whether *action* grants a Focused Will stack.

        Args:
            action: Action name.

        Returns:
            True if the action grants a stack on damage.
        """
        return action.upper() in SHOJIN_STACK_GRANTING_ACTIONS

    def modifier_dict(self) -> Dict[str, Any]:
        """Return a damage_modifier dict for ``calculate_damage()``.

        Returns:
            Dict with name and amp keys.
        """
        return {"name": self.name, "amp": self.damage_amp()}
