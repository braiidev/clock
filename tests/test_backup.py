"""Tests para services.backup."""

import json
import os

from clock_tui.services.backup import backup_data, restore_from_file


def test_backup_creates_copy(tmp_path):
    data = {"version": 7, "alarms": []}
    data_file = tmp_path / "data.json"
    data_file.write_text(json.dumps(data))
    dest = tmp_path / "backups"
    dest.mkdir()

    ok, path = backup_data(str(data_file), str(dest))

    assert ok
    assert os.path.exists(path)
    with open(path, "r", encoding="utf-8") as f:
        assert json.load(f)["version"] == 7


def test_restore_valid(tmp_path):
    data_file = tmp_path / "data.json"
    data_file.write_text('{"version": 7, "old": true}')
    backup = tmp_path / "backup.json"
    backup.write_text('{"version": 7, "old": false, "nuevo": 1}')

    ok, msg, contenido = restore_from_file(str(backup), str(data_file))

    assert ok
    assert "nuevo" in contenido
    with open(data_file, "r", encoding="utf-8") as f:
        assert json.load(f)["nuevo"] == 1


def test_restore_invalid_json(tmp_path):
    data_file = tmp_path / "data.json"
    data_file.write_text("{}")
    backup = tmp_path / "bad.json"
    backup.write_text("no es json")

    ok, msg, contenido = restore_from_file(str(backup), str(data_file))

    assert ok is False
    assert "inválido" in msg
    assert contenido is None


def test_restore_missing_file(tmp_path):
    data_file = tmp_path / "data.json"
    data_file.write_text("{}")

    ok, msg, contenido = restore_from_file(str(tmp_path / "no.json"), str(data_file))

    assert ok is False
