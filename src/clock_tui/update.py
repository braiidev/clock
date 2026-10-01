"""Self-update vía git (patrón tplay).

El paquete corre desde un clone de git (`install.sh` lo instala editable desde
`~/.local/share/clock-tui`), así que la raíz del repo es `parents[2]` de este
módulo (clock_tui/update.py → src → raíz).

La actualización se decide **por commits** (`git rev-list --count HEAD..origin/main`),
no por comparación semántica de versiones: eso lo hace inmune al defasaje entre
el contador de tasks (v0.N) y el semver de producto (v1.y.z en pyproject).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path

from . import __version__
from .core.store import CONFIG_DIR

GIT_TIMEOUT = 8
PULL_TIMEOUT = 30

# Nombre del archivo donde install.sh persiste la ruta versionada del intérprete
# con la que se creó el venv. Ver install.sh para el porqué (symlink flotante).
PINNED_FILE = ".pinned-python"

_lock = threading.Lock()


def repo_root() -> str:
    """Raíz del repo git que contiene este paquete (install desde clone)."""
    return str(Path(__file__).resolve().parents[2])


def pinned_python(repo: str | None = None) -> str | None:
    """Ruta del intérprete pineado por install.sh, o None si no hay pin."""
    try:
        raw = (Path(repo or repo_root()) / PINNED_FILE).read_text().strip()
    except OSError:
        return None
    return raw or None


def sync_pinned_python(repo: str | None = None, exe: str | None = None) -> str | None:
    """Realinea `.pinned-python` con el intérprete que realmente está corriendo.

    El pin existe para que install.sh no se desvíe a otra versión en la próxima
    corrida. Si el venv se rehizo a mano (o install.sh corrió en otra máquina),
    el pin queda mintiendo y eso termina en el mismo ModuleNotFoundError del
    upgrade de SO. Devuelve el valor anterior si hubo que corregirlo, None si
    ya estaba bien o si el layout es inesperado (preferimos no escribir antes
    que dejar un pin basura).
    """
    base = Path(repo or repo_root())
    candidate = os.path.realpath(exe or sys.executable)
    if not os.path.basename(candidate).startswith("python3"):
        return None
    if str(Path(sys.prefix).resolve()) in candidate:
        return None  # venv con --copies: no sirve como pin
    old = pinned_python(str(base))
    if old == candidate:
        return None
    try:
        (base / PINNED_FILE).write_text(candidate + "\n")
    except OSError:
        return None
    return old or "(ninguno)"


def _git(
    repo: str, args: list[str], timeout: int = GIT_TIMEOUT
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, timeout=timeout
    )


def _describe(repo: str, rev: str) -> str:
    try:
        r = _git(repo, ["describe", "--tags", rev, "--abbrev=0"])
        if r.returncode == 0:
            return r.stdout.strip()
        s = _git(repo, ["rev-parse", "--short", rev])
        if s.returncode == 0:
            return s.stdout.strip()
    except Exception:
        pass
    return rev[:7]


@dataclass
class UpdateInfo:
    ok: bool
    error: str | None = None
    behind: int = 0
    current: str = ""
    available: str = ""


def check_update(repo: str) -> UpdateInfo:
    """Devuelve cuántos commits está detrás `repo` respecto de origin/main."""
    with _lock:
        return _check_update_unlocked(repo)


def _check_update_unlocked(repo: str) -> UpdateInfo:
    if not os.path.isdir(os.path.join(repo, ".git")):
        return UpdateInfo(False, "no es un repositorio git")
    try:
        f = _git(repo, ["fetch", "origin"], timeout=GIT_TIMEOUT)
        if f.returncode != 0:
            return UpdateInfo(False, (f.stderr.strip() or "fetch falló"))
        r = _git(repo, ["rev-list", "--count", "HEAD..origin/main"])
        if r.returncode != 0:
            return UpdateInfo(False, (r.stderr.strip() or "rev-list falló"))
        behind = int((r.stdout or "0").strip() or 0)
        return UpdateInfo(
            ok=True,
            behind=behind,
            current=_describe(repo, "HEAD"),
            available=_describe(repo, "origin/main"),
        )
    except FileNotFoundError:
        return UpdateInfo(False, "git no está instalado")
    except Exception as e:  # noqa: BLE001
        return UpdateInfo(False, str(e))


@dataclass
class UpdateResult:
    ok: bool
    message: str


def do_update(repo: str) -> UpdateResult:
    """Aplica la actualización si hay commits detrás. Si falla el pull, resetea."""
    with _lock:
        info = _check_update_unlocked(repo)
        if not info.ok:
            return UpdateResult(False, f"No se pudo verificar: {info.error}")
        if info.behind == 0:
            stale = sync_pinned_python(repo)
            if stale:
                return UpdateResult(
                    True,
                    f"Estás al día ({info.current}) — intérprete pineado corregido "
                    f"(era {stale})",
                )
            return UpdateResult(True, f"Estás al día ({info.current})")
        pull = _git(repo, ["pull", "--ff-only"], timeout=PULL_TIMEOUT)
        if pull.returncode == 0:
            _pip_reinstall(repo)
            sync_sounds(repo)
            sync_pinned_python(repo)
            return UpdateResult(True, f"Actualizado a {info.available} — reiniciá")
        reset = _git(repo, ["reset", "--hard", "origin/main"], timeout=15)
        if reset.returncode == 0:
            _pip_reinstall(repo)
            sync_sounds(repo)
            sync_pinned_python(repo)
            return UpdateResult(
                True, f"Actualizado a {info.available} (historial corregido) — reiniciá"
            )
        return UpdateResult(False, f"Falló el pull: {pull.stderr.strip()}")


def _pip_reinstall(repo: str) -> None:
    """Refresca el paquete editable del venv si el repo corre desde uno."""
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", repo],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=PULL_TIMEOUT,
        )
    except Exception:
        pass


def sync_sounds(repo: str, dest: str | None = None) -> int:
    """Copia los sonidos empaquetados del repo a la carpeta de audios del usuario.

    Solo agrega archivos que falten (nunca pisa los que el usuario ya tenga,
    para que sus personalizaciones sobrevivan a cada actualización). Devuelve
    la cantidad de archivos copiados.
    """
    src = os.path.join(repo, "src", "clock_tui", "sounds")
    if not os.path.isdir(src):
        return 0
    target = dest or os.path.join(CONFIG_DIR, "sounds")
    os.makedirs(target, exist_ok=True)
    copied = 0
    for name in os.listdir(src):
        src_file = os.path.join(src, name)
        if not os.path.isfile(src_file):
            continue
        dst_file = os.path.join(target, name)
        if not os.path.exists(dst_file):
            try:
                shutil.copy2(src_file, dst_file)
                copied += 1
            except OSError:
                pass
    return copied


def is_auto_update_enabled() -> bool:
    return os.environ.get("CLOCK_NO_AUTO_UPDATE", "0").lower() not in (
        "1",
        "true",
        "yes",
    )


__all__ = [
    "__version__",
    "UpdateInfo",
    "UpdateResult",
    "check_update",
    "do_update",
    "is_auto_update_enabled",
    "pinned_python",
    "repo_root",
    "sync_pinned_python",
    "sync_sounds",
]
