"""Tests para core.time_utils."""

from clock_tui.core.time_utils import hms_to_secs, secs_to_hms


def test_hms_roundtrip():
    assert hms_to_secs(1, 2, 3) == 3723
    assert secs_to_hms(3723) == (1, 2, 3)


def test_secs_to_hms_edge_cases():
    assert secs_to_hms(0) == (0, 0, 0)
    assert secs_to_hms(59) == (0, 0, 59)
    assert secs_to_hms(3600) == (1, 0, 0)
    assert secs_to_hms(3661) == (1, 1, 1)


def test_secs_to_hms_clamps_negative():
    assert secs_to_hms(-5) == (0, 0, 0)


def test_hms_to_secs_zero_leading():
    assert hms_to_secs(0, 0, 0) == 0
    assert hms_to_secs(2, 30, 15) == 9015
