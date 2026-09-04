"""Tests para services.audio."""

import os

from clock_tui.services.audio import _SOUND_EXTS, resolve_sound_path


def test_sound_exts():
    assert ".wav" in _SOUND_EXTS
    assert ".mp3" in _SOUND_EXTS


def test_resolve_sound_path_default(tmp_path):
    audio_file = tmp_path / "bell.ogg"
    audio_file.write_bytes(b"x")
    config = {"sonido_modo": "default", "sonido_archivo": "bell.ogg"}
    assert resolve_sound_path(config, str(tmp_path)) == str(audio_file)


def test_resolve_sound_path_default_none(tmp_path):
    config = {"sonido_modo": "default", "sonido_archivo": None}
    assert resolve_sound_path(config, str(tmp_path)) is None


def test_resolve_sound_path_custom(tmp_path):
    custom = tmp_path / "custom.mp3"
    custom.write_bytes(b"x")
    config = {"sonido_modo": "custom", "sonido_custom_path": str(custom)}
    assert resolve_sound_path(config, str(tmp_path)) == str(custom)


def test_resolve_sound_path_custom_missing(tmp_path):
    config = {"sonido_modo": "custom", "sonido_custom_path": str(tmp_path / "no.mp3")}
    assert resolve_sound_path(config, str(tmp_path)) is None
