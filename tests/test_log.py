"""Tests para core.log."""

import json

import clock_tui.core.log as log


def test_log_roundtrip(tmp_path, monkeypatch):
    log.LOG_FILE = str(tmp_path / "log.jsonl")
    log._log_error("un error")
    log._log_error("otro", trace="tb")

    entries = log._log_read_all()
    assert len(entries) == 2
    assert entries[0]["msg"] == "un error"
    assert entries[1]["trace"] == "tb"
    assert all(not e["visto"] for e in entries)
    assert log._log_has_unseen() is True


def test_log_mark_all_seen(tmp_path, monkeypatch):
    log.LOG_FILE = str(tmp_path / "log.jsonl")
    log._log_error("e1")
    log._log_error("e2")

    log._log_mark_all_seen()

    entries = log._log_read_all()
    assert all(e["visto"] for e in entries)
    assert log._log_has_unseen() is False


def test_log_missing_file(tmp_path, monkeypatch):
    log.LOG_FILE = str(tmp_path / "no_existe.jsonl")
    assert log._log_read_all() == []
    assert log._log_has_unseen() is False


def test_log_skips_corrupt_line(tmp_path, monkeypatch):
    log.LOG_FILE = str(tmp_path / "log.jsonl")
    with open(log.LOG_FILE, "w", encoding="utf-8") as f:
        f.write('{"msg": "ok", "visto": false}\n')
        f.write("no json\n")
    entries = log._log_read_all()
    assert len(entries) == 1
    assert entries[0]["msg"] == "ok"
