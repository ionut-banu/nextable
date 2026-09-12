"""Wait estimation, spec section 6.

Pure by construction: it takes a bucket's numbers, a list of turnaround
samples, and a count of parties ahead, and returns an integer. No database
access, no clock reads. Every rule in section 6 is a test in
tests/test_estimator.py.
"""
import math
from collections.abc import Sequence

from app.models import SizeBucket


def bucket_for_size(size: int) -> SizeBucket:
    if size <= 2:
        return SizeBucket.SMALL
    if size <= 4:
        return SizeBucket.MEDIUM
    if size <= 6:
        return SizeBucket.LARGE
    return SizeBucket.XLARGE


def effective_turn_minutes(
    samples: Sequence[float],
    default_turn_minutes: float,
    history_window: int,
    smoothing_constant: float,
) -> float:
    """Blend observed turnarounds toward the configured prior (spec 6.2).

    effective_turn = (n * observed_avg + m * default_turn) / (n + m)

    With no history this is exactly the configured default. As real data
    arrives the prior fades.
    """
    window = list(samples)[-history_window:] if history_window > 0 else []
    n = len(window)
    if n == 0:
        return float(default_turn_minutes)

    observed_avg = sum(window) / n
    m = smoothing_constant
    return (n * observed_avg + m * default_turn_minutes) / (n + m)


def estimate_wait_minutes(
    *,
    parties_ahead: int,
    samples: Sequence[float],
    default_turn_minutes: float,
    table_count: int,
    history_window: int,
    smoothing_constant: float,
) -> int:
    """The quote (spec 6.3), rounded up to the nearest five minutes.

    Zero parties ahead means zero: we can seat you now.
    """
    if parties_ahead <= 0:
        return 0

    rounds = math.ceil(parties_ahead / max(1, table_count))
    turn = effective_turn_minutes(
        samples, default_turn_minutes, history_window, smoothing_constant
    )
    return round_up_to_five(rounds * turn)


def round_up_to_five(minutes: float) -> int:
    return int(math.ceil(minutes / 5) * 5)
