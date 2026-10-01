# TODO

## Doing
*(vacío)*

## Next
- [ ] v1.2.26 fix: `test_footer_oculto_si_no_cabe_o_config_off` falla en `tests/test_app.py:189` — roto desde el commit `v0.55 style: micro una linea` (no está en el Done de abajo). No lo toqué: ajeno al batch FIX

### 🔧 FIX — el venv flotante NO se reparaba, y `clock --update` no lo reparaba — CERRADO v0.57
Diagnóstico: v0.56 evitaba que se *crearan* venvs flotantes, pero no reparaba los que ya existían. Y `clock --update` solo hacía `git pull` + `pip install -e`, así que jamás ejecutaba `install.sh`.

- [x] v0.57a: `venv_flota()` en install.sh — detecta el alias flotante recorriendo el enlace. `venv_ok` la consulta, así que un venv flotante se recrea con la ruta versionada
- [x] v0.57b: `venv_is_floating(repo)` en update.py — espejo en Python, porque resolver la ruta no los distingue
- [x] v0.57c: `run_installer(repo)` — `do_update` delega en el `install.sh` del repo (fuente única de cómo se arma el entorno). Con commits nuevos siempre corre; sin novedad solo si el venv está flotante
- [x] v0.57d: detección de recreado vía `.venv/.created-at` (timestamp con nanosegundos que install.sh escribe al recrear), para poder decir "reiniciá clock"

**Tres bugs que aparecieron al testear el escenario real** (ninguno se veía leyendo el código):
1. `venv_ok` comparaba rutas **resueltas**: un venv flotante resuelve a la misma ruta que uno sano (`/usr/bin/python3.12`), así que pasaba por sano y el fix nunca se aplicaba. Resolver a `realpath` —el arreglo anterior— borraba justo la información que distingue los dos casos.
2. Detectar el recreado con `os.stat` no funciona: sigue el symlink y ve el mismo inode antes y después. Con `lstat` tampoco: al borrar y recrear el symlink el filesystem **reutiliza** el inode. Lo resuelve un timestamp escrito por install.sh.
3. `do_update` con `behind == 0` respondía "Estás al día" sin mirar el venv. Ese fue el silencio que reportó el usuario: hizo el update, todo seemed bien, y la protección seguía sin aplicarse.

**Verificación:** `pytest` → 545 passed, 1 failed (preexistente, ver `Next`). E2E en HOME aislado con un venv creado **a la vieja** (`python3 -m venv`): install.sh lo detecta y recrea; `clock --update` lo repara solo y avisa "venv recreado con ruta versionada, reiniciá clock"; el segundo update no toca nada; `~/.config/clock/` intacto.

### 🔧 FIX — install.sh sobrevive al upgrade a Ubuntu 26.04 (Python 3.14) — CERRADO v0.56

**Síntoma:** en la máquina `.38` (actualizada 24.04 → 26.04) `clock` dejó de arrancar.

**Causa raíz — el symlink flotante, no el número de versión.** `python3 -m venv` crea el venv así:

```
.venv/bin/python -> python3
.venv/bin/python3 -> /usr/bin/python3     ← flotante
```

`/usr/bin/python3` es un symlink que **siempre** resuelve a la última versión instalada. El venv
declara `version = 3.12.3` en `pyvenv.cfg` pero ejecuta lo que haya. Al subir a 26.04 el shebang de
`.venv/bin/clock` siguió resolviendo (ahora era 3.14), así que no hubo "comando no encontrado":
corrió un 3.14 dentro de un venv con layout 3.12 → buscó `lib/python3.14/site-packages`, no lo
encontró, y el install editable quedó invisible → `ModuleNotFoundError: clock_tui`.

**Trampa de fondo:** como `~/.local/bin/clock` era `ln -sf` al venv, en cuanto se rompió tampoco se
podía correr `clock --update` para repararlo. La salida de emergencia estaba dentro de lo roto.

**Verificado empíricamente** (3 formas de crear venv, mismo repo):

| Método | `.venv/bin/python` apunta a | ¿Sobrevive upgrade del SO? |
|---|---|---|
| `python3 -m venv` | `/usr/bin/python3` ← flotante | ❌ se rompe en silencio |
| `python3.14 -m venv` | `/usr/bin/python3.14` | ✅ |
| `uv venv --python /usr/bin/python3.14` | `/usr/bin/python3.14` | ✅ |

**Decisión para clock — opción B: Python del sistema versionado, detectado.** Invocar la ruta
versionada (`/usr/bin/python3.14 -m venv`) en vez del symlink flotante, y **grabar la versión pineada
en un archivo** para que `--update` sepa qué validar. Justificación: clock tiene `dependencies = []`
— es stdlib puro, no hay una sola extensión compilada. Meterle uv agregaría una dependencia que se
puede romper y no compra nada (0 MB, sin red para el intérprete). Cuando `/usr/bin/python3` pase a
3.15, `/usr/bin/python3.14` sigue existiendo y el venv sigue funcionando.

- [x] v0.56: `requires-python` de `>=3.9` a `>=3.10,<3.15` (el rango abierto no impedía que un install tomara 3.14). **Sin** `uv.lock`: sin deps no hay nada que resolver
- [x] v0.57: install.sh — resolver el `/usr/bin/python3.X` versionado más nuevo del rango y **persistirlo en `.pinned-python`**. Se reescribe siempre: si el pineado murió, se realinea al nuevo
- [x] v0.58: install.sh — recrear el venv invocado con la ruta versionada (`"$PY" -m venv`), nunca con `python3`. Auto-repara si `.venv/bin/python` no responde, si su `realpath` ≠ el pin, o si `import clock_tui` falla
- [x] v0.59: wrapper `~/.local/bin/clock` en vez de symlink — dos guards (intérprete muerto / editable invisible) y mensaje con el comando exacto de reparación. `prepare_bin` con marcador: respalda binarios ajenos y reemplaza symlinks viejos. `ensure_path` al rc correcto (zsh vs bash) e idempotente
- [x] v0.60: `update.py` — `pinned_python(repo)` y `sync_pinned_python(repo, exe)` parametrizadas para test; `do_update` las invoca con `repo`. `_pip_reinstall()` intacto (el venv se crea con pip)
- [x] v0.61: smoke test final (`clock --version`) con salida ≠ 0 si falla. Overrides `CLOCK_TUI_DIR` / `CLOCK_TUI_BIN` / `CLOCK_TUI_RC` para testear sin tocar el HOME real
- [x] v0.62: `.pinned-python` al `.gitignore` + 8 tests del pin + `~/Dev/Clock/.venv` regenerado con intérprete versionado (el viejo quedó en `.venv.stale-20261001/`; su `pyvenv.cfg` apuntaba a `Dev/_scripts/Clock/.venv`, ruta inexistente) + CLOCK.md/README

**Entrega:** un commit (v0.56-v0.62 unificados) + `git tag v0.56`, con este bloque como registro.

**Dos bugs que aparecieron al testear el escenario de rompimiento real** (invisibles leyendo el código):
1. `venv_ok` comparaba la versión (`3.12`) contra el pin, que guarda una **ruta** (`/usr/bin/python3.12`) → nunca coincidían y el install caía siempre en "recrear". Canonizado todo a `realpath`.
2. El pin **nunca se reescribía**: tras recrear el venv con otro intérprete, `venv_ok` comparaba contra el pin viejo y daba falso negativo, dejando el install en error aunque el venv estuviera sano.

**Verificación:** `pytest` → 533 passed, 1 failed (preexistente, ver `Next`). End-to-end en HOME aislado: install sano → layout roto → el wrapper avisa con el comando exacto → `install.sh` repara solo → `--uninstall` borra wrapper y código conservando los datos. Idempotente en la segunda corrida.

**No tocar:** `sync_sounds()` sigue copiando a `~/.config/clock/sounds` sin pisar; `--uninstall` sigue
funcionando (`os.unlink` borra igual symlink o archivo regular, y `repo_root()` resuelve al mismo dir).

**Nota:** los install.sh se sirven desde `raw.githubusercontent.com/braiidev/clock/main/install.sh`.
El fix no llega a otra máquina hasta que esté pusheado a `main`.

## Done
- [x] v1.2.25: Listas usan toda la altura: quitar caps _MAX_VISIBLE cuando hay capacity real - v0.54
- [x] v1.2.24: Overlay <o> scrolleable con jk/flechas (router + draw_activity con ventana y contador) - v0.53
- [x] v1.2.23: Micro vistas: config `micro_mostrar` (Todo/Fecha y hora/Solo hora/Solo clima) + draw_micro 2 líneas + app - v0.52
- [x] v1.2.22: Responsive 3 estados: micro h<3, full h≥8, mini en medio (size_tier + tests) - v0.51
- [x] v1.2.21: Docs tiers responsive 3 estados (micro/mini/full) por altura + aclaración micro MVP (D20) - v0.50
- [x] v1.2.20: Contador (n/N) en el borde inferior también en Dashboard (siempre, hasta con 1 ítem) y Config (scroll+contador nuevos) - v0.49
- [x] v1.2.19: Scroll: selección siempre visible (fix filas fijas TODO/stopwatch) + contador (n/N) en el borde inferior para todas las listas (alarms/timers/todo/clock WC/picker/crono) - v0.48
- [x] v1.2.18: Sonidos bundled en el paquete — install.sh/--update los copian a ~/.config/clock/sounds (sin pisar) + fallback bundled - v0.46
- [x] v1.2.17: Scroll/truncate normalizado por altura (frame + todos los views + dashboard + overlay <o>) - v0.45
- [x] v1.2.16: Nav configurable (mostrar_nav) y oculto en mínima si no cabe - v0.44
- [x] v1.2.15: Ayuda — cada vista/?: coherencia con su controller (a ≠ n, r no R, crono ≠ to-do) - v0.43
- [x] v1.2.14: Reloj — WC muestran diferencia local-wc - v0.41
- [x] v1.2.13: Dashboard — "Próxima alarma" muestra el día (desambiguar 1d+ de repetición) - v0.40
- [x] v1.2.12: hjkl espejo de flechas en editores/selectores - v0.39
- [x] v1.2.11: Dashboard — navegación persiste (arrows y hjkl arreglados) - v0.38
- [x] v1.2.10: Auditoría (pytest/pyright/black) + docs + bump semver 1.2.0 - v0.36
- [x] v1.2.9: Config — selector ►, Data→Sistema, tema Flatline, alarmas_mostrar en Dashboard - v0.35
- [x] v1.2.8: Dashboard — próxima alarma por recurrencia (_next_occurrence) + color clima - v0.34
- [x] v1.2.7: Reloj — WCs como filas con ►, scroll window, wc_mostrar funcional - v0.33
- [x] v1.2.6: Navegación hjkl (alarms, timers, dashboard, clock) - v0.32
- [x] v1.2.5: Reorden con J/K (alarms, timers, world_clocks persistido) - v0.31
- [x] v1.2.4: Confirmar borrado con y/Y/s/S (timers nuevo + accept en alarms/todo/clock) - v0.30
- [x] v1.2.3: Captura de teclas durante edición/confirmación (globals ignoradas si el feature edita) - v0.29
- [x] v1.2.2: Auditoría final — pyright 0 errores (store/theme/world_zones/weather) + black 26 uniforme + revisión rendimiento/concurrencia/legibilidad - v0.28
- [x] v1.2.1: Overlay de actividad `<o>` (alarmas/timers/crono/tareas con orden, `alarmas_mostrar` cableado) - v0.27
- [x] v1.1.4: doc CLOCK.md (instalación/actualización/desinstalación, convención de versionado) + push a braiidev/clock - v0.25
- [x] Fase 6.3: cierre — doc fase 5/6 en CLOCK.md, limpieza (removido clock.py), milestone **v1.0** - v0.21
- [x] Fase 6.2: validación en terminal real (pty) por vista + resize/micro + KEY_RESIZE handler - v0.20
- [x] Fase 6.1: tests de integración app — flows e2e vía dispatch + renders de overlays + bug edit_state alarmas - v0.19
- [x] Fase 5.6: main.py funcional (curses.wrapper + crash log) + pyproject script + verificación en pty real - v0.17
- [x] Fase 5.5: app.py — dashboard jump/refresh + config commands + overlays - v0.16
- [x] Fase 5.4: app.py — ticks de fondo (timers/alarmas/snooze) + alert overlay + audio - v0.15
- [x] Fase 5.3: app.py — bootstrap + persistencia + main loop + dispatch + render + quit - v0.14
- [x] Fase 5.2: unificar firma de view.render (theme, pairs, config) según D15 - v0.13
- [x] Fase 5.1: router global de navegación (módulo puro + 16 tests) - v0.12
- [x] Fase 4: features MVC — stopwatch ✅ timers ✅ alarms ✅ clock ✅ dashboard ✅ todo ✅ config ✅ - v0.11
- [x] Fase 3: UI toolkit (responsive 2 tiers, frame, overlay, browser) - v0.3
- [x] Fase 2: servicios (store v7+migración, theme, log, weather, audio, backup) - v0.2
- [x] Fase 1: utilidades puras (time_utils, recurrence, world_zones) - v0.1
- [x] Fase 0: consolidar documentación en CLOCK.md y eliminar previas - v0.0