"""Tests para ui.browser.list_entries."""

from clock_tui.ui.browser import list_entries


def test_list_entries_sound_filters(tmp_path):
    (tmp_path / "subdir").mkdir()
    (tmp_path / "bell.wav").write_bytes(b"x")
    (tmp_path / "music.ogg").write_bytes(b"x")
    (tmp_path / "nota.txt").write_text("no")

    entries = list_entries(str(tmp_path), "sound")

    names = [n for n, _ in entries]
    dirs = [n for n, es_dir in entries if es_dir]
    files = [n for n, es_dir in entries if not es_dir]
    assert dirs == ["subdir"]
    assert set(files) == {"bell.wav", "music.ogg"}
    assert "nota.txt" not in names
    # directorios primero
    assert entries[0] == ("subdir", True)


def test_list_entries_restore_filters(tmp_path):
    (tmp_path / "backup.json").write_text("{}")
    (tmp_path / "a.txt").write_text("x")
    entries = list_entries(str(tmp_path), "restore")
    files = [n for n, es_dir in entries if not es_dir]
    assert files == ["backup.json"]


def test_list_entries_missing_dir(tmp_path):
    assert list_entries(str(tmp_path / "no_existe"), "sound") == []
