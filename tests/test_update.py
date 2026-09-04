"""Tests de update.py: check/do con repos git locales simulando origin."""

from __future__ import annotations

import os
import shutil
import subprocess

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
