"""Wait estimation, spec section 6. Pure: no database, no clock."""
import pytest

from app.models import SizeBucket
from app.services.estimator import (
    bucket_for_size,
    effective_turn_minutes,
    estimate_wait_minutes,
)

SMALL_TURN, SMALL_TABLES = 25, 8
LARGE_TURN, LARGE_TABLES = 55, 3
WINDOW, SMOOTHING = 20, 5


def quote(parties_ahead, samples, turn=SMALL_TURN, tables=SMALL_TABLES):
    return estimate_wait_minutes(
        parties_ahead=parties_ahead,
        samples=samples,
        default_turn_minutes=turn,
        table_count=tables,
        history_window=WINDOW,
        smoothing_constant=SMOOTHING,
    )


@pytest.mark.parametrize(
    "size,bucket",
    [
        (1, SizeBucket.SMALL),
        (2, SizeBucket.SMALL),
        (3, SizeBucket.MEDIUM),
        (4, SizeBucket.MEDIUM),
        (5, SizeBucket.LARGE),
        (6, SizeBucket.LARGE),
        (7, SizeBucket.XLARGE),
        (24, SizeBucket.XLARGE),
    ],
)
def test_bucket_boundaries(size, bucket):
    assert bucket_for_size(size) == bucket


def test_no_history_returns_the_configured_default():
    assert effective_turn_minutes([], SMALL_TURN, WINDOW, SMOOTHING) == 25


@pytest.mark.parametrize("n,expected", [(1, 30.0), (5, 40.0), (20, 49.0)])
def test_blend_shrinks_toward_the_prior(n, expected):
    # (n * observed + m * prior) / (n + m), prior 25, m 5, every sample 55.
    assert effective_turn_minutes([55] * n, SMALL_TURN, WINDOW, SMOOTHING) == expected


def test_window_keeps_only_the_last_n_samples():
    with_old_outliers = [200] * 5 + [55] * 20
    assert effective_turn_minutes(with_old_outliers, SMALL_TURN, WINDOW, SMOOTHING) == 49.0


def test_zero_parties_ahead_gives_zero():
    assert quote(0, []) == 0
    assert quote(0, [90] * 20, turn=LARGE_TURN, tables=LARGE_TABLES) == 0


def test_capacity_divides_the_queue():
    assert quote(1, []) == 25
    assert quote(8, []) == 25
    assert quote(9, []) == 50


def test_rounds_up_to_five_minutes():
    # Prior 25 blended with a single 28 gives 25.5, which quotes as 30.
    assert quote(1, [28]) == 30


def test_learned_turnarounds_move_the_quote():
    cold = quote(3, [], turn=LARGE_TURN, tables=LARGE_TABLES)
    learned = quote(3, [80] * 20, turn=LARGE_TURN, tables=LARGE_TABLES)
    assert cold == 55
    assert learned == 75
