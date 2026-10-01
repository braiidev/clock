# TODO

## Doing
*(vacío — esperando OK para arrancar el batch FIX Python 3.14)*

## Next

### 🔧 FIX — install.sh sobrevive al upgrade a Ubuntu 26.04 (Python 3.14)

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

- [ ] v0.56: acota `requires-python` de `>=3.9` a `>=3.10,<3.15` (el rango abierto no impedía que un install tomara 3.14). **Sin** `uv.lock`: sin deps no hay nada que resolver
- [ ] v0.57: install.sh — resolver el `/usr/bin/python3.X` versionado más nuevo dentro del rango y **persistirlo en `.pinned-python`**. Sin ese archivo, el venv se recrea contra un intérprete distinto al que se creó
- [ ] v0.58: install.sh — recrear el venv invocado con la ruta versionada (`"$PY" -m venv`), nunca con `python3`. Auto-reparar si `.venv/bin/python` no responde o su versión ≠ la pineada
- [ ] v0.59: wrapper `~/.local/bin/clock` en vez de symlink — valida venv + versión pineada, y si está roto repara o imprime el comando exacto. Cierra el agujero de "el comando mismo está muerto"
- [ ] v0.60: `update.py` — `do_update()` valida la versión pineada y reconstruye el venv si el SO\subió de minor; `_pip_reinstall()` sigue usando `sys.executable -m pip` (el venv se crea con pip, no con `--seed`)
- [ ] v0.61: smoke test final (`clock --version`) con salida ≠ 0 si falla + append idempotente de `~/.local/bin` al PATH (hoy solo avisa y nunca escribe)
- [ ] v0.62: regenerar `~/Dev/Clock/.venv` stale (su `pyvenv.cfg` graba `command = .../Dev/_scripts/Clock/.venv`, path que ya no existe) + test del escenario real (venv con intérprete flotante → se detecta y repara) + CLOCK.md/README

**Entrega:** un solo commit (v0.56-v0.62 unificados) + `git tag v0.56`, con este bloque como registro.

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