"""Tests para features.alarms.model."""

import datetime

from clock_tui.features.alarms.model import Alarm, AlarmsModel, SnoozeEntry


def test_alarm_defaults():
    a = Alarm()
    assert a.nombre == "Alarma"
    assert a.hora == 0
    assert a.minutos == 0
    assert a.status == "activado"
    assert a.repeat_days == []


def test_alarm_is_enabled():
    assert Alarm(status="activado").is_enabled() is True
    assert Alarm(status="desactivado").is_enabled() is False


def test_alarm_toggle():
    a = Alarm(status="activado")
    a.toggle()
    assert a.status == "desactivado"
    a.toggle()
    assert a.status == "activado"


def test_alarm_repeat_str():
    assert Alarm(repeat_days=[]).repeat_str() == "una vez"
    assert Alarm(repeat_days=[0, 1, 2, 3, 4]).repeat_str() == "L-V"
    assert Alarm(repeat_days=[0, 1, 2, 3, 4, 5, 6]).repeat_str() == "todos"
    assert Alarm(repeat_days=[5, 6]).repeat_str() == "S-D"


def test_from_data():
    data = [
        {"nombre": "R", "hora": 15, "minutos": 0, "status": "activado", "repeat_days": [0, 1]},
        {"nombre": "D", "hora": 7, "minutos": 30, "status": "desactivado", "repeat_days": []},
    ]
    m = AlarmsModel.from_data(data)
    assert len(m.alarms) == 2
    assert m.alarms[0].nombre == "R"
    assert m.alarms[0].repeat_days == [0, 1]
    assert m.alarms[1].status == "desactivado"


def test_to_data():
    m = AlarmsModel(
        alarms=[Alarm(nombre="X", hora=8, minutos=0, repeat_days=[0])]
    )
    d = m.to_data()
    assert len(d) == 1
    assert d[0]["tipo"] == "alarma"
    assert d[0]["hora"] == 8
    assert d[0]["repeat_days"] == [0]


def test_check_fires_matching():
    m = AlarmsModel(
        alarms=[Alarm(hora=10, minutos=30, status="activado")]
    )
    now = datetime.datetime(2025, 6, 16, 10, 30)  # Monday
    fired = m.check(now)
    assert len(fired) == 1
    assert fired[0][0].status == "disparada"


def test_check_no_fire_wrong_time():
    m = AlarmsModel(
        alarms=[Alarm(hora=10, minutos=30, status="activado")]
    )
    now = datetime.datetime(2025, 6, 16, 10, 31)
    fired = m.check(now)
    assert len(fired) == 0


def test_check_no_fire_disabled():
    m = AlarmsModel(
        alarms=[Alarm(hora=10, minutos=30, status="desactivado")]
    )
    now = datetime.datetime(2025, 6, 16, 10, 30)
    fired = m.check(now)
    assert len(fired) == 0


def test_check_repeats_reactivates():
    m = AlarmsModel(
        alarms=[Alarm(hora=10, minutos=30, status="activado", repeat_days=[0, 1, 2, 3, 4])]
    )
    now = datetime.datetime(2025, 6, 16, 10, 30)  # Monday
    m.check(now)
    assert m.alarms[0].status == "disparada"
    now2 = datetime.datetime(2025, 6, 16, 10, 31)
    m.check(now2)
    assert m.alarms[0].status == "activado"


def test_check_once_deactivates():
    m = AlarmsModel(
        alarms=[Alarm(hora=10, minutos=30, status="activado", repeat_days=[])]
    )
    now = datetime.datetime(2025, 6, 16, 10, 30)
    m.check(now)
    now2 = datetime.datetime(2025, 6, 16, 10, 31)
    m.check(now2)
    assert m.alarms[0].status == "desactivado"


def test_check_no_duplicate_same_minute():
    m = AlarmsModel(
        alarms=[Alarm(hora=10, minutos=30, status="activado")]
    )
    now = datetime.datetime(2025, 6, 16, 10, 30)
    m.check(now)
    fired2 = m.check(now)
    assert len(fired2) == 0


def test_check_wrong_day():
    m = AlarmsModel(
        alarms=[Alarm(hora=10, minutos=30, status="activado", repeat_days=[5, 6])]
    )
    now = datetime.datetime(2025, 6, 16, 10, 30)  # Monday=0
    fired = m.check(now)
    assert len(fired) == 0


def test_check_snoozes_fires():
    m = AlarmsModel()
    m.snoozes.append(SnoozeEntry(hora=10, minutos=30, nombre="Test"))
    now = datetime.datetime(2025, 6, 16, 10, 30)
    fired = m.check_snoozes(now)
    assert len(fired) == 1
    assert len(m.snoozes) == 0


def test_check_snoozes_no_fire_early():
    m = AlarmsModel()
    m.snoozes.append(SnoozeEntry(hora=10, minutos=30, nombre="Test"))
    now = datetime.datetime(2025, 6, 16, 10, 29)
    fired = m.check_snoozes(now)
    assert len(fired) == 0


def test_create_snooze():
    m = AlarmsModel()
    now = datetime.datetime(2025, 6, 16, 10, 0)
    m.create_snooze("Test", 5, now)
    assert len(m.snoozes) == 1
    assert m.snoozes[0].hora == 10
    assert m.snoozes[0].minutos == 5


def test_clamp_scroll():
    m = AlarmsModel(
        alarms=[Alarm(nombre=f"A{i}") for i in range(10)],
        selected_idx=8,
    )
    m._clamp_scroll()
    assert m.scroll_offset == 3
