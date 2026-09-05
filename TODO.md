# TODO

## Doing
- [ ] v1.2.22: Responsive 3 estados: micro h<3, full h≥8, mini en medio (size_tier + tests) - v0.51

## Next
- [ ] v1.2.23: Micro vistas: config `micro_mostrar` (Todo/Fecha y hora/Solo hora/Solo clima) + draw_micro 2 líneas + app - v0.52
- [ ] v1.2.24: Overlay <o> scrolleable con jk/flechas (router + draw_activity con ventana y contador) - v0.53
- [ ] v1.2.25: Listas usan toda la altura: quitar caps _MAX_VISIBLE cuando hay capacity real - v0.54

## Done
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