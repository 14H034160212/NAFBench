"""Cluster-aware confidence intervals.

Audit finding #3: our eval sets contain many prompts that are theme-replicates
and repeated-sampling copies of a SMALL number of distinct certified programs.
Feeding prompt-level trials into a Wilson interval as if they were independent
Bernoulli draws understates uncertainty (pseudoreplication) -- the real
independent unit is the PROGRAM, not the prompt.

`cluster_bootstrap_ci` resamples whole programs (with replacement) and pools
their trials, so the interval reflects program-level, not decoder-level,
uncertainty. With only a handful of programs it is honestly wide.
"""
from __future__ import annotations
import random
from typing import Dict, List, Tuple


def cluster_bootstrap_ci(prog_to_trials: Dict[str, List[int]],
                         B: int = 2000, seed: int = 0
                         ) -> Tuple[float, float, float, int, int, int]:
    """Cluster (program) bootstrap for a binary accuracy.

    prog_to_trials: program-id -> list of 0/1 outcomes (all its prompt trials).
    Returns (point, lo, hi, k, n, n_programs) where point/k/n are the pooled
    prompt-level estimate and [lo, hi] is the 95% program-clustered CI.
    """
    progs = [p for p, t in prog_to_trials.items() if t]
    n_prog = len(progs)
    all_trials = [x for p in progs for x in prog_to_trials[p]]
    k, n = sum(all_trials), len(all_trials)
    if n == 0 or n_prog == 0:
        return (float("nan"), float("nan"), float("nan"), 0, 0, 0)
    point = k / n
    if n_prog == 1:
        # can't bootstrap across clusters; report the point estimate as the band
        return (point, point, point, k, n, n_prog)
    rng = random.Random(seed)
    means = []
    for _ in range(B):
        pooled = []
        for _ in range(n_prog):
            pooled.extend(prog_to_trials[progs[rng.randrange(n_prog)]])
        if pooled:
            means.append(sum(pooled) / len(pooled))
    means.sort()
    lo = means[int(0.025 * len(means))]
    hi = means[int(0.975 * len(means)) - 1]
    return (point, lo, hi, k, n, n_prog)
