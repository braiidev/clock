"""Tests de update.py: check/do con repos git locales simulando origin."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

import pytest

from clock_tui import update

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None, reason="git no está instalado"
)


def _run(repo: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)


def _init_repo(tmp_path, name: str) -> str:
    repo = str(tmp_path / name)
    os.makedirs(repo)
    r = _run(repo, "init", "-q", "-b", "main")
    if r.returncode != 0:
        _run(repo, "init", "-q")
        _run(repo, "symbolic-ref", "HEAD", "refs/heads/main")
    _run(repo, "config", "user.email", "test@clock.local")
    _run(repo, "config", "user.name", "Test")
    _run(repo, "config", "commit.gpgsign", "false")
    return repo


def _commit(repo: str, content: str) -> None:
    with open(os.path.join(repo, "src_clock_tui_data.txt"), "a", encoding="utf-8") as f:
        f.write(content + "\n")
    _run(repo, "add", "-A")
    assert _run(repo, "commit", "-q", "-m", content).returncode == 0


@pytest.fixture
def git_pair(tmp_path):
    """Crea un origin (A) y un clone instalado (B)."""
    origin = _init_repo(tmp_path, "origin")
    _commit(origin, "v1")
    clone = str(tmp_path / "instalado")
    subprocess.run(["git", "clone", "-q", origin, clone], check=True)
    _run(clone, "config", "commit.gpgsign", "false")
    return origin, clone


def test_check_update_up_to_date(git_pair):
    _, clone = git_pair
    info = update.check_update(clone)
    assert info.ok is True
    assert info.behind == 0


def test_check_update_behind_commits(git_pair):
    origin, clone = git_pair
    _commit(origin, "v2")
    _commit(origin, "v3")
    info = update.check_update(clone)
    assert info.ok is True
    assert info.behind == 2
    assert len(info.current) == 7  # describe de HEAD (sin tags) = hash corto


def test_do_update_pulls(git_pair):
    origin, clone = git_pair
    _commit(origin, "v2")
    res = update.do_update(clone)
    assert res.ok is True
    assert "Actualizado" in res.message
    head = _run(clone, "rev-parse", "HEAD").stdout.strip()
    origin_head = _run(origin, "rev-parse", "HEAD").stdout.strip()
    assert head == origin_head


def test_do_update_up_to_date(git_pair):
    _, clone = git_pair
    res = update.do_update(clone)
    assert res.ok is True
    assert "al día" in res.message


def test_do_update_reset_fallback_on_diverged(git_pair):
    origin, clone = git_pair
    _commit(clone, "cambio local")  # historia divergida: pull --ff-only falla
    _commit(origin, "v2")
    res = update.do_update(clone)
    assert res.ok is True
    assert "historial corregido" in res.message
    head = _run(clone, "rev-parse", "HEAD").stdout.strip()
    origin_head = _run(origin, "rev-parse", "HEAD").stdout.strip()
    assert head == origin_head


def test_check_update_not_a_repo(tmp_path):
    not_repo = str(tmp_path / "norepo")
    os.makedirs(not_repo)
    info = update.check_update(not_repo)
    assert info.ok is False
    assert "repositorio" in (info.error or "")


def test_check_update_without_origin(tmp_path):
    solo = _init_repo(tmp_path, "solo")
    _commit(solo, "v1")
    info = update.check_update(solo)
    assert info.ok is False


def test_is_auto_update_enabled(monkeypatch):
    monkeypatch.setenv("CLOCK_NO_AUTO_UPDATE", "0")
    assert update.is_auto_update_enabled() is True
    monkeypatch.setenv("CLOCK_NO_AUTO_UPDATE", "1")
    assert update.is_auto_update_enabled() is False
    monkeypatch.setenv("CLOCK_NO_AUTO_UPDATE", "")
    assert update.is_auto_update_enabled() is True


def test_repo_root_resolves_to_repo_layout():
    root = update.repo_root()
    assert os.path.isdir(os.path.join(root, "src", "clock_tui"))
    assert os.path.isfile(os.path.join(root, "pyproject.toml"))


def _repo_con_sonidos(tmp_path) -> str:
    repo = str(tmp_path / "repo")
    snd = os.path.join(repo, "src", "clock_tui", "sounds")
    os.makedirs(snd)
    for nom, content in [("bell.oga", "beep"), ("galaxy.mp3", "audio")]:
        with open(os.path.join(snd, nom), "w", encoding="utf-8") as f:
            f.write(content)
    return repo


def test_sync_sounds_copia_solo_faltantes(tmp_path):
    repo = _repo_con_sonidos(tmp_path)
    dest = str(tmp_path / "dest")
    os.makedirs(dest)
    with open(os.path.join(dest, "galaxy.mp3"), "w", encoding="utf-8") as f:
        f.write("custom del usuario")  # NO debe pisarse

    copied = update.sync_sounds(repo, dest)

    with open(os.path.join(dest, "galaxy.mp3"), encoding="utf-8") as f:
        assert f.read() == "custom del usuario"
    with open(os.path.join(dest, "bell.oga"), encoding="utf-8") as f:
        assert f.read() == "beep"
    assert copied == 1


def test_sync_sounds_sin_carpeta_devuelve_cero(tmp_path):
    assert update.sync_sounds(str(tmp_path), str(tmp_path / "nada")) == 0


# ── .pinned-python ──
# El pin existe porque `python3 -m venv` deja .venv/bin/python3 -> /usr/bin/python3
# (symlink flotante). Al subir el SO el venv queda con layout de una versión e
# intérprete de otra y clock muere con ModuleNotFoundError. install.sh guarda acá
# la ruta versionada con la que se creó el venv para no desviarse en la próxima.


def _fake_interp(tmp_path, name: str = "python3.14") -> str:
    """Intérprete falso pero ejecutable, para no depender del SO en el test."""
    d = tmp_path / "interps"
    d.mkdir(exist_ok=True)
    p = d / name
    p.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    p.chmod(0o755)
    return str(p)


def test_pinned_python_sin_archivo_devuelve_none(tmp_path):
    assert update.pinned_python(str(tmp_path)) is None


def test_pinned_python_lee_el_archivo(tmp_path):
    (tmp_path / update.PINNED_FILE).write_text("/usr/bin/python3.14\n")
    assert update.pinned_python(str(tmp_path)) == "/usr/bin/python3.14"


def test_pinned_python_archivo_vacio_devuelve_none(tmp_path):
    (tmp_path / update.PINNED_FILE).write_text("   \n")
    assert update.pinned_python(str(tmp_path)) is None


def test_sync_pinned_escribe_cuando_no_hay_pin(tmp_path):
    exe = _fake_interp(tmp_path)
    viejo = update.sync_pinned_python(str(tmp_path), exe)
    assert viejo == "(ninguno)"
    assert update.pinned_python(str(tmp_path)) == str(
        tmp_path / "interps" / "python3.14"
    )


def test_sync_pinned_no_toca_si_ya_es_el_mismo(tmp_path):
    exe = _fake_interp(tmp_path)
    update.sync_pinned_python(str(tmp_path), exe)
    assert update.sync_pinned_python(str(tmp_path), exe) is None


def test_sync_pinned_corrige_pin_desfasado(tmp_path):
    """El caso del upgrade de SO: el pin apunta a una versión que ya no existe."""
    (tmp_path / update.PINNED_FILE).write_text("/usr/bin/python3.12-QUE-NO-EXISTE\n")
    exe = _fake_interp(tmp_path, "python3.14")
    viejo = update.sync_pinned_python(str(tmp_path), exe)
    assert viejo == "/usr/bin/python3.12-QUE-NO-EXISTE"
    assert update.pinned_python(str(tmp_path)) == str(
        tmp_path / "interps" / "python3.14"
    )


def test_sync_pinned_rechaza_ejecutable_inesperado(tmp_path):
    """Con layout raro preferimos no escribir antes que dejar un pin basura."""
    exe = _fake_interp(tmp_path, "python-real")
    assert update.sync_pinned_python(str(tmp_path), exe) is None
    assert update.pinned_python(str(tmp_path)) is None


def test_sync_pinned_rechaza_interprete_dentro_del_venv(tmp_path, monkeypatch):
    """venv creado con --copies: realpath cae adentro y no sirve como pin."""
    venv = tmp_path / "venv"
    exe = venv / "bin" / "python3.14"
    exe.parent.mkdir(parents=True)
    exe.write_text("#!/bin/sh\n", encoding="utf-8")
    exe.chmod(0o755)
    monkeypatch.setattr(sys, "prefix", str(venv))
    assert update.sync_pinned_python(str(tmp_path), str(exe)) is None
    assert update.pinned_python(str(tmp_path)) is None
