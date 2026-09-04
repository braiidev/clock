"""Tests para features.clock.world_zones."""

import datetime

from clock_tui.features.clock.world_zones import (
    WORLD_ZONES,
    _wc_format_diff,
    _wc_offset_info,
    _wc_sorted_zones,
    _wc_zone_lookup,
)

REF = datetime.datetime(2026, 9, 4, 12, 0, tzinfo=datetime.timezone.utc)


def test_world_zones_size_and_lookup():
    assert len(WORLD_ZONES) == 47
    assert _wc_zone_lookup("UTC")[0] == "UTC"
    assert _wc_zone_lookup("no_existe") == ("no_existe", "no_existe", "?", "?", "NO_E")


def test_offset_info_known_zone():
    info = _wc_offset_info("UTC", ref=REF)
    assert info is not None
    # Para UTC el utcoffset es siempre 0 (determinista); el diff con hora local
    # depende del timezone del host y se cubre en el test de orden relativo.
    dt, _diff = info
    assert dt == REF
    assert dt.utcoffset() == datetime.timedelta(0)


def test_offset_info_invalid_zone():
    assert _wc_offset_info("no_existe", ref=REF) is None


def test_format_diff():
    assert _wc_format_diff(0) == "+0"
    assert _wc_format_diff(180) == "+3"
    assert _wc_format_diff(195) == "+3.15"
    assert _wc_format_diff(-90) == "-1.30"


def test_sorted_zones_utc_first_order():
    s = _wc_sorted_zones(None, ref=REF)
    assert s[0][0] == "Pacific/Midway" or s[-1][0] == "Pacific/Kiritimati"
    # el orden es por offset creciente: el primero debe ser el mas lejano al Oeste
    first = _wc_offset_info(s[0][0], ref=REF)
    last = _wc_offset_info(s[-1][0], ref=REF)
    assert first is not None and last is not None
    assert first[1] < last[1]
