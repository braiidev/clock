"""Tests para features.clock.model."""

import datetime

from clock_tui.features.clock.model import ClockModel, WorldClock


def _model(wc_list=None) -> ClockModel:
    return ClockModel(wc_list=wc_list or [])


def test_format_local_time_24h():
    now = datetime.datetime(2025, 6, 16, 14, 5, 9)
    assert ClockModel.format_local_time(now) == "14:05:09"


def test_format_local_time_12h():
    now = datetime.datetime(2025, 6, 16, 14, 5, 9)
    assert ClockModel.format_local_time(now, format_24h=False) == "02:05:09 PM"


def test_format_local_time_no_seconds():
    now = datetime.datetime(2025, 6, 16, 14, 5, 9)
    assert ClockModel.format_local_time(now, show_seconds=False) == "14:05"


def test_format_date_line():
    now = datetime.datetime(2025, 6, 16, 14, 5, 9)
    result = ClockModel.format_date_line(now, "14:05:09")
    assert "Lun" in result
    assert "16" in result
    assert "Jun" in result
    assert "14:05:09" in result


def test_wc_add():
    m = _model()
    m.wc_add("America/New_York", "NY")
    assert len(m.wc_list) == 1
    assert m.wc_list[0].zona == "America/New_York"
    assert m.wc_list[0].apodo == "NY"


def test_wc_update():
    m = _model([WorldClock("UTC", "U")])
    m.wc_update(0, "Europe/London", "Lon")
    assert m.wc_list[0].zona == "Europe/London"
    assert m.wc_list[0].apodo == "Lon"


def test_wc_delete():
    m = _model([WorldClock("UTC", "U"), WorldClock("Asia/Tokyo", "TYO")])
    m.wc_idx = 1
    m.wc_delete(0)
    assert len(m.wc_list) == 1
    assert m.wc_list[0].zona == "Asia/Tokyo"


def test_nav_wc_wraps():
    m = _model([WorldClock("UTC", "U"), WorldClock("Asia/Tokyo", "TYO")])
    m.wc_idx = 1
    m.nav_wc(1)
    assert m.wc_idx == 0


def test_nav_wc_empty_does_nothing():
    m = _model()
    m.nav_wc(1)
    assert m.wc_idx == 0


def test_wc_swap_swaps_list():
    m = _model([WorldClock("UTC", "U"), WorldClock("Asia/Tokyo", "TYO")])
    m.wc_swap(0, 1)
    assert m.wc_list[0].zona == "Asia/Tokyo"
    assert m.wc_list[1].zona == "UTC"


def test_nav_wc_clamps_scroll():
    wcs = [WorldClock("UTC", f"W{i}") for i in range(6)]
    m = _model(wcs)
    m.wc_idx = 0
    for _ in range(4):
        m.nav_wc(1)
    assert m.wc_idx == 4
    assert m.wc_scroll == 1
    for _ in range(4):
        m.nav_wc(-1)
    assert m.wc_idx == 0
    assert m.wc_scroll == 0


def test_wc_delete_clamps_idx():
    m = _model([WorldClock("UTC", "U"), WorldClock("Asia/Tokyo", "TYO")])
    m.wc_idx = 1
    m.wc_delete(1)
    assert m.wc_idx == 0


def test_picker_open():
    m = _model()
    m.picker_open()
    assert m.picker.open is True
    assert len(m.picker.zones) > 0


def test_picker_close():
    m = _model()
    m.picker_open()
    m.picker_close()
    assert m.picker.open is False


def test_picker_nav():
    m = _model()
    m.picker_open()
    initial = m.picker.idx
    m.picker_nav(1)
    assert m.picker.idx == initial + 1


def test_picker_nav_wraps():
    m = _model()
    m.picker_open()
    m.picker.idx = 0
    m.picker_nav(-1)
    assert m.picker.idx == len(m.picker.zones) - 1


def test_picker_confirm_zone():
    m = _model()
    m.picker_open()
    m.picker_confirm_zone()
    assert m.edit_nick.active is True
    assert m.picker.open is False


def test_edit_nick_commit():
    m = _model()
    m.picker_open()
    m.picker_confirm_zone()
    m.edit_nick.temp_name = "MiReloj"
    wc = m.edit_nick_commit()
    assert wc is not None
    assert wc.apodo == "MiReloj"
    assert m.edit_nick.active is False


def test_edit_nick_commit_empty_uses_code():
    m = _model()
    m.picker_open()
    m.picker_confirm_zone()
    zona_code = m.edit_nick.zona[4]
    m.edit_nick.temp_name = ""
    wc = m.edit_nick_commit()
    assert wc is not None
    assert wc.apodo == zona_code


def test_edit_nick_cancel():
    m = _model()
    m.picker_open()
    m.picker_confirm_zone()
    m.edit_nick_cancel()
    assert m.edit_nick.active is False
    assert m.picker.open is False


def test_wc_time_str():
    m = _model()
    result = m.wc_time_str("UTC")
    assert ":" in result


def test_wc_diff_str():
    m = _model()
    result = m.wc_diff_str("UTC")
    assert "UTC" in result


def test_wc_local_diff_str(monkeypatch):
    import os
    import time as t

    old_tz = os.environ.get("TZ")
    monkeypatch.setenv("TZ", "America/Argentina/Buenos_Aires")
    t.tzset()
    try:
        m = _model()
        assert m.wc_local_diff_str("UTC") == "(-3h)"
        assert m.wc_local_diff_str("America/Argentina/Buenos_Aires") == ""
    finally:
        if old_tz is not None:
            os.environ["TZ"] = old_tz
        else:
            os.environ.pop("TZ", None)
        t.tzset()


def test_wc_local_diff_str_invalida():
    m = _model()
    assert m.wc_local_diff_str("Zona/Inexistente") == ""
