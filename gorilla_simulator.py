"""Battle simulator: 100 men versus one angry gorilla.

This module provides a very small, self-contained Monte-Carlo simulator that
models what might happen if a group of human fighters were to confront a single
gorilla.  The numbers used in the simulation are obviously fictional – the goal
is to explore *possible* outcomes, not to make definitive scientific claims.

Usage
-----
The module can be executed directly.  Running the script will perform a batch
of simulated fights and print a short report with summary statistics.

The behaviour of the simulation can be tuned via command line flags.  For
example, to run 10,000 trials with a custom random seed you could execute:

```
python gorilla_simulator.py --trials 10000 --seed 123
```

The parameters that govern the fighters – health, damage ranges, and so on –
are exposed via dataclasses, so advanced experiments can be carried out by
importing the module and instantiating the appropriate configuration objects.
"""

from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass
from typing import Iterable, List, Sequence


@dataclass(frozen=True)
class CombatProfile:
    """Parameter bundle describing a combatant.

    Attributes
    ----------
    name:
        Human-readable label for the combatant type.
    health:
        Initial hit points.  When a combatant's health reaches zero or below
        they are removed from combat.
    damage_min / damage_max:
        Bounds for the uniform random damage that the combatant deals whenever
        they land a hit.  Damage is sampled as an integer.
    attacks_per_round:
        Number of distinct hits the combatant attempts to make per round.
        Humans strike once per round while the gorilla is able to dish out
        several hits in quick succession.
    critical_chance:
        Probability of an attack dealing an additional burst of damage.  This
        adds some swinginess to outcomes without making the code much more
        complicated.
    critical_multiplier:
        Multiplier that is applied to the base damage when a critical strike
        occurs.  Values greater than 1.0 increase the damage of a crit, while
        values of exactly 1.0 effectively disable critical hits.
    """

    name: str
    health: int
    damage_min: int
    damage_max: int
    attacks_per_round: int
    critical_chance: float = 0.05
    critical_multiplier: float = 1.5

    def sample_damage(self, rng: random.Random) -> int:
        base_damage = rng.randint(self.damage_min, self.damage_max)
        if self.critical_chance > 0 and rng.random() < self.critical_chance:
            return math.ceil(base_damage * self.critical_multiplier)
        return base_damage


@dataclass
class Combatant:
    """Concrete fighter taking part in the battle."""

    profile: CombatProfile
    health: int

    @classmethod
    def from_profile(cls, profile: CombatProfile) -> "Combatant":
        return cls(profile=profile, health=profile.health)

    @property
    def alive(self) -> bool:
        return self.health > 0

    def apply_damage(self, amount: int) -> None:
        self.health -= amount


def create_men(count: int, profile: CombatProfile) -> List[Combatant]:
    return [Combatant.from_profile(profile) for _ in range(count)]


def simulate_battle(
    men: Sequence[Combatant],
    gorilla: Combatant,
    rng: random.Random,
) -> str:
    """Run a single battle simulation.

    Parameters
    ----------
    men:
        A sequence of human combatants.
    gorilla:
        The gorilla combatant.
    rng:
        Random number generator controlling the stochastic behaviour.

    Returns
    -------
    str
        "men" if at least one human remains alive, otherwise "gorilla".
    """

    men_alive: List[Combatant] = list(men)

    max_men_attackers = 12

    while men_alive and gorilla.alive:

        # Men attack first this round.  Only a handful can reach the gorilla at
        # any moment, so we cap the number of simultaneous attackers.
        attackers = men_alive if len(men_alive) <= max_men_attackers else rng.sample(
            men_alive, max_men_attackers
        )
        total_damage = 0
        for man in attackers:
            damage = man.profile.sample_damage(rng)
            total_damage += damage
        gorilla.apply_damage(total_damage)

        if not gorilla.alive:
            return "men"

        # Gorilla retaliates, selecting distinct targets at random when
        # possible.  The gorilla may repeat targets if fewer men remain than
        # their number of attacks.
        if men_alive:
            target = rng.choice(men_alive)
        else:
            target = None
        for _ in range(gorilla.profile.attacks_per_round):
            if not men_alive or target is None:
                break
            damage = gorilla.profile.sample_damage(rng)
            target.apply_damage(damage)
            if not target.alive:
                men_alive.remove(target)
                target = rng.choice(men_alive) if men_alive else None

    return "men" if men_alive else "gorilla"


def run_trials(
    trials: int,
    men_profile: CombatProfile,
    gorilla_profile: CombatProfile,
    rng: random.Random,
) -> dict:
    """Execute many battles and collect summary statistics."""

    wins = {"men": 0, "gorilla": 0}
    for _ in range(trials):
        men = create_men(100, men_profile)
        gorilla = Combatant.from_profile(gorilla_profile)
        outcome = simulate_battle(men, gorilla, rng)
        wins[outcome] += 1
    return wins


def parse_args(args: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=1000, help="Number of fights to simulate")
    parser.add_argument("--seed", type=int, default=None, help="Optional random seed")
    parser.add_argument(
        "--men-health",
        type=int,
        default=100,
        help="Initial health for each man",
    )
    parser.add_argument(
        "--gorilla-health",
        type=int,
        default=2300,
        help="Initial health for the gorilla",
    )
    return parser.parse_args(args)


def main(namespace: argparse.Namespace) -> None:
    rng = random.Random(namespace.seed)

    men_profile = CombatProfile(
        name="Man",
        health=namespace.men_health,
        damage_min=3,
        damage_max=6,
        attacks_per_round=1,
        critical_chance=0.05,
        critical_multiplier=2.0,
    )

    gorilla_profile = CombatProfile(
        name="Angry Gorilla",
        health=namespace.gorilla_health,
        damage_min=60,
        damage_max=110,
        attacks_per_round=4,
        critical_chance=0.1,
        critical_multiplier=2.3,
    )

    results = run_trials(namespace.trials, men_profile, gorilla_profile, rng)

    print("Simulation complete")
    print(f"Trials run: {namespace.trials}")
    if namespace.seed is not None:
        print(f"Random seed: {namespace.seed}")

    men_win_rate = results["men"] / namespace.trials
    gorilla_win_rate = results["gorilla"] / namespace.trials

    print(f"Men victories:     {results['men']} ({men_win_rate:.1%})")
    print(f"Gorilla victories: {results['gorilla']} ({gorilla_win_rate:.1%})")


if __name__ == "__main__":
    main(parse_args())
