# CLOCK — Documento único del proyecto

Guía de referencia para el refactor de `clock.py` (TUI en curses) a un paquete
instalable `clock-tui`. Este documento consolida y resuelve las discrepancias
entre la documentación previa. Es la única fuente de verdad;
---

## 0. Decisiones cerradas

| # | Decisión |
|---|---|
| D1 | Framework: **curses** (stdlib), refactor dentro de curses |
| D2 | Packaging: **paquete instalable** (`pyproject.toml` + `pipx`) |
| D3 | **Pomodoro eliminado** (vista, lógica y dato de persistencia) |
| D4 | Navegación: **híbrido** `[` `]` + `0-6` directo |
| D5 | Tecla "añadir" universal: **`a`** (nunca `n` ni `c`) |
| D6 | Reset: **`r` individual**, sin `R` global |
| D7 | **Panel de notas eliminado** (notas y tareas en la misma lista ToDo) |
| D8 | Clima: **wttr.in** |
| D9 | Dashboard `Enter` → saltar a vista: **sí** |
| D10 | Responsive: **2 tiers** (micro / full), sin `minimum` |
| D11 | Alarmas: **vista separada** (no dentro de Reloj) |
| D12 | Persistencia: **`data.json` + version 7**, migración automática desde `clock_data.json` v6 |

---

## 1. Arquitectura y packaging

```
clock-tui/
├── pyproject.toml               # name="clock-tui"; [project.scripts] clock-tui = "clock_tui.main:main"
├── src/
│   └── clock_tui/
│       ├── __init__.py          # __version__
│       ├── main.py              # Entry point, curses.wrapper
│       ├── core/
│       │   ├── app.py           # Event loop, view dispatcher, estado global mínimo
│       │   ├── router.py        # Input routing: global → vista → sub-vista
│       │   ├── store.py         # Persistencia JSON (~/.config/clock/data.json) + migración
│       │   ├── theme.py         # Temas, color pairs, SET_CUSTOM_THEME
│       │   ├── log.py           # Error logging
│       │   ├── time_utils.py    # secs_to_hms, hms_to_secs
│       │   └── recurrence.py    # DIAS_ABBR, repeat_days, todo_is_done/set_done
│       ├── services/
│       │   ├── weather.py       # wttr.in + cache + retry + thread background
│       │   ├── audio.py         # Fallback chain (ffplay→paplay→aplay→beep)
│       │   └── backup.py        # Backup/restore JSON
│       ├── ui/
│       │   ├── frame.py         # draw_box, draw_frame, centered, ellipsis, badge
│       │   ├── overlay.py       # Alert modal, Help overlay, Log viewer
│       │   ├── browser.py       # File browser (sonidos, restore)
│       │   └── responsive.py    # size_tier (micro/full), scroll helpers
│       └── features/
│           ├── dashboard/       # model.py + controller.py + view.py
│           ├── clock/           # model.py + controller.py + view.py + world_zones.py
│           ├── alarms/          # model.py + controller.py + view.py
│           ├── timers/          # model.py + controller.py + view.py
│           ├── stopwatch/       # model.py + controller.py + view.py
│           ├── todo/            # model.py + controller.py + view.py
│           └── config/          # model.py + controller.py + view.py
└── tests/
```

**Patrón MVC por feature:**
- **model.py** → Estado (dataclass/dict) + validaciones. Sin I/O, sin curses.
- **controller.py** → Lógica de negocio. Recibe `(model, key, context)` → muta modelo → retorna `ActionResult`. Es lo que hoy son `_input_X`.
- **view.py** → Rendering puro. Recibe `(model, stdscr, theme, tier)` → dibuja, sin mutar estado. Es lo que hoy son `_draw_X`.

**Instalación:** `pipx install -e .` → comando global `clock-tui`.

---

## 2. Responsive: 2 tiers

### Tier `micro` (w<40 AND h<5)
- Sin marco.
- Título de tab en `H=0` (alineado izquierda, `PAIR_MARCO`).
- Contenido centrado; si excede el ancho, se trunca con ellipsis (`…`).
- Footer `H=h-1` compacto: `[0-6 q]`.
- Sin helpers, sin badge, sin clima.
- Sin sub-vistas (editores, confirmaciones, pickers): se ignoran o muestran mensaje de 1 línea.

### Tier `full` (todo lo demás)
- Marco con `draw_box` (si `mostrar_marco`).
- Contenido centrado dentro del marco.
- Helpers debajo del marco (si `mostrar_helpers`).
- Badge de actividad sobre el footer.
- Footer con modo + tab bar expandido.
- Listas con scroll e indicador `(1–6 de 12)`.
- Texto que excede el ancho → ellipsis.
- Sub-vistas se renderizan dentro del marco.

### Ellipsis y scroll
| Situación | Comportamiento |
|---|---|
| Texto > ancho | Truncar con `…` al final |
| Lista > alto | Scroll con `↑↓`, indicador `(1–N de M)` |
| Item seleccionado sale del viewport | Auto-scroll |
| Micro: texto > ancho | Truncar con `…`, sin scroll |

---

## 3. Navegación

### Tab bar (footer, tier full)
```
── NORMAL ── Dash · Reloj · Alarm · Timer · Crono · ToDo · Conf  q ──
```
- Tab activa: `A_REVERSE` o `A_BOLD`.
- `[` `]` ciclan (wrap-around). `0-6` acceso directo. Micro: `[0-6 q]`.

| Tecla | Tab | Título frame |
|---|---|---|
| `0` | Dash | `◈ Dashboard` |
| `1` | Reloj | `◷ Reloj` |
| `2` | Alarm | `◷ Alarmas` |
| `3` | Timer | `⏱ Timers` |
| `4` | Crono | `⏲ Cronómetro` |
| `5` | ToDo | `▤ ToDo` |
| `6` | Conf | `⚙ Configuración` |

**Nota:** Son 7 vistas (0-6). No hay Pomodoro ni Panel de notas.

---

## 4. Teclas normalizadas

### Globales (siempre activas)
| Tecla | Acción |
|---|---|
| `q` | Salir (guarda estado) |
| `?` | Toggle help overlay |
| `0-6` | Acceso directo a vista |
| `[` `]` | Ciclar vistas |
| `Esc` | Contextual: en edición/confirmación → cancelar; en normal → pause/play global |

### Navegación (dentro de vistas)
| Tecla | Acción |
|---|---|
| `h`/`←`, `j`/`↓`, `k`/`↑`, `l`/`→` | Mover / navegar |
| `Enter` | Confirmar / seleccionar / guardar |
| `Esc` | Cancelar / volver |

### CRUD (consistente en TODAS las vistas con items)
| Tecla | Acción |
|---|---|
| `a` | Añadir/Crear (universal, nunca `n`/`c`) |
| `e` | Editar |
| `d` | Eliminar (con confirmación `y`/`Enter`) |
| `Space` | Toggle (on/off, play/pause, done/undone) |
| `r` | Reset del item seleccionado (sin `R` global) |

### Modo edición (formulario activo)
| Tecla | Acción |
|---|---|
| `↑↓`/`jk` | Navegar campos |
| `←→`/`hl` | Ajustar valor del campo activo |
| `Tab` | Ciclar sub-campos (HH↔MM, tipo↔nota) |
| `Space` | Toggle en booleanos |
| `Enter` | Guardar / avanzar |
| `Esc` | Cancelar |

### Específicas por vista
| Vista | Tecla | Acción |
|---|---|---|
| Reloj | `u` | Refresh clima manual |
| Reloj | `f` | Filtro en picker de WC |
| Cronómetro | `m` | Marcar lap (solo corriendo) |
| ToDo | `x` | Toggle recordatorio |
| Config | `←→` | Cambiar categoría/tab |

### Eliminadas / libres
- `n` (nuevo) → reemplazada por `a`.
- `R` (reset global) → no existe, solo `r`.
- `o` (panel notas) → eliminado. **Queda libre.**
- `Tab` (lap en crono) → reemplazada por `m`; `Tab` se reserva para sub-campos.

---

## 5. Vistas

### Vista 0 — Dashboard
Resumen de solo lectura: fecha+hora, clima, próxima alarma (countdown), timers activos, crono activo, tareas pendientes, pospuestas.

```
┌──────────────────────────────────────┐
│          [ ◈ Dashboard ]             │
│                                      │
│  Lun 16 Jun  14:32:05                │
│  ※ Buenos Aires: +12°C  (hace 5m)    │
│   ________________________________   │
│  ◷ Próx: Reunión 15:00 ↻L-V (en 28m) │ ← de aqui para abajo seleccionables-navegables
│  ⏱ Timer1  08:22                     │
│  ▤ 3 tareas pendientes (2/5)         │
│  💤 1 pospuesta(s)                   │
│                                      │
└──────────────────────────────────────┘
```
**`Enter` (D9):** salta a la vista correspondiente con el item seleccionado. El Dashboard mantiene un `selected_item_idx` que mapea a `(vista, item_idx)`. Sub-vistas: ninguna.

### Vista 1 — Reloj
Reloj local centrado + gestión de relojes mundiales + clima. Teclas: `↑↓` sección, `←→` WC, `a`+WC, `e` editar, `d` borrar, `u` clima.

```
┌──────────────────────────────────────┐
│            [ ◷ Reloj ]               │
│                                      │
│     Lun 16 Jun  14:32:05             │
│                                      │
│  »BUE 14:32«  NY 13:32  LON 18:32    │
│                                      │
└──────────────────────────────────────┘
  ↑↓:sección  ←→:WC  a:+WC  e:editar  d:borrar  u:clima
```
Sub-vistas: Picker de zona (~47 zonas IANA ordenadas por offset, filtro `f`, máx 10 visibles con scroll) → Editor de apodo (muestra zona + diff UTC, input libre) → Confirmación borrado.

### Vista 2 — Alarmas
CRUD de alarmas con repetición semanal. Contenido: status (✔/✘), nombre, HH:MM, días. Teclas: `↑↓`, `a`, `e`, `d`, `Space` on/off.

```
┌──────────────────────────────────────┐
│           [ ◷ Alarmas ]              │
│                                      │
│ ► ✔ Reunión     15:00  ↻L-V          │
│   ✘ Despertar   07:00  ↻todos        │
│   ✔ Backup      23:00  una vez       │
│                                      │
└──────────────────────────────────────┘
  a:nueva  ↑↓:nav  Space:on/off  e:editar  d:borrar
```
Editor de alarma (3 campos): Nombre (typing, `Backspace`), Hora HH:MM (`↑↓` selecciona, `Tab` cicla HH↔MM, `←→` ajusta), Días (`←→` cursor, `Space` toggle). `Enter` avanza Nombre→Hora→Días→guarda. Máx 6 visibles con indicador.

### Vista 3 — Timers
Temporizadores countdown con nombre. Límite: máx 10. Teclas: `↑↓` nav, `a` nuevo, `e` editar nombre, `d` borrar, `Space` play/pause, `r` reset seleccionado, `Tab` ciclar HH↔MM↔SS (solo pausado), `←→` ajustar valor.

```
┌──────────────────────────────────────┐
│           [ ⏱ Timers ]               │
│                                      │
│ ►▶ Timer1       [08:22:15]           │
│   Timer2       [10:00:00]            │
│   Timer3       [◄00►:15:00]          │
│                                      │
└──────────────────────────────────────┘
  a:nuevo  ↑↓:nav  Tab:campo  ←→:valor  Space:▶/❚❚  e:editar  d:borrar  r:reset
```
Comportamiento: al llegar a 0 dispara Alert con `alarm_ref=t`; al cerrar con `Space`/`Enter` se resetea al tiempo original. `r` para (si corre) y resetea. `Space` a 0 reinicia y arranca. `Tab`/`←→` solo si pausado.

### Vista 4 — Cronómetro
Stopwatch con laps (efímero, no persiste). Teclas: `Space` play/pause, `m` lap (solo corriendo), `d` borrar último lap, `r` reset total.

```
┌──────────────────────────────────────┐
│         [ ⏲ Cronómetro ]             │
│                                      │
│ ▶ 00:12:34.56                        │
│                                      │
│ ►  3.  00:12:34   (+00:04:12)        │
│    2.  00:08:22   (+00:03:55)        │
│    1.  00:04:27   (+00:04:27)        │
│                                      │
└──────────────────────────────────────┘
  Space:▶/❚❚  m:marcar lap  d:borrar último  r:reset
```
Máx 5 laps visibles con scroll. `m` en vez de `Tab` (reservado a sub-campos).

### Vista 5 — ToDo
Tareas y notas en la misma lista, con recordatorios. Iconos: ✔/☐ (tarea), ✎ (nota). Teclas: `↑↓` nav, `←→` reordenar, `a` nuevo, `e` editar, `d` borrar, `Space` toggle done (solo tareas), `x` toggle recordatorio.

```
┌──────────────────────────────────────┐
│            [ ▤ ToDo ]                │
│  14:32:05                            │
│                                      │
│ ► ☐ Comprar leche  ⟳L-V 07:00       │
│   ✓ Enviar informe ◷16/06 15:00     │
│   ✎ Ideas para el proyecto           │
│   ☐ Llamar al médico                 │
│                                      │
└──────────────────────────────────────┘
  a:nuevo  ↑↓:nav  ←→:mover  Space:✔/○  e:editar  d:borrar  x:alarma
```
Sin panel lateral (`o` eliminado). Máx 8 visibles con scroll.

Editor de item (campos dinámicos):
| Campo | Tarea | Nota |
|---|---|---|
| Tipo (Tarea/Nota) | ✔ | ✔ |
| Texto | ✔ | ✔ |
| Recordarme | ✔ | ✘ |
| Repetir (semanal) | ✔ (si recordarme) | ✘ |
| Días (L-V) | ✔ (si repetir) | ✘ |
| Hora | ✔ (si recordarme) | ✘ |
| Minuto | ✔ (si recordarme) | ✘ |
| Día/Mes/Año | ✔ (si no repetir) | ✘ |

`Tab`/`Space` en booleanos; `←→` en numéricos; `←→`+`Space` en días; `Enter` guarda, `Esc` cancela.

### Vista 6 — Config
Tabs por categoría + items configurables. Teclas: `←→` tab, `↑↓` nav, `Space`/`Enter` toggle/ciclar/ejecutar. Sub-vistas: editor de texto, file browser, log viewer.

```
┌──────────────────────────────────────┐
│       [ ⚙ Configuración ]            │
│                                      │
│ [Apariencia]  Reloj  Clima  Sonido  Data │
│                                      │
│ ► Tema de color           [Clasico]  │
│   Mostrar marco           [✔ ON ]    │
│   Mostrar segundos        [✔ ON ]    │
│                                      │
└──────────────────────────────────────┘
  ←→:categoría  ↑↓:nav  Space/Enter:toggle/ciclar/elegir
```

Categorías:
- **Apariencia:** Tema (clasico/mono/calido/alto_contraste/custom), colores custom (marco, texto, clima, helpers, nav), mostrar marco, mostrar helpers.
- **Reloj:** Mostrar segundos, formato 24h, posponer alarma (min), badge modo, mostrar WC, mostrar alarmas.
- **Clima:** Mostrar clima, ubicación, intervalo auto-update, mostrar "hace N min", reintentos máx, espera entre reintentos.
- **Sonido:** Sonido ON/OFF, origen (default/custom), archivo default, archivo custom (browser).
- **Data:** Crear backup, restaurar backup, ver log de errores, exportar log.

Tipos de item: `bool` (toggle ✔/✘), `choice` (cicla), `text` (editor inline), `soundfile` (cicla archivos de `~/.config/clock/sounds/`), `soundbrowser` (abre browser), `soundmode` (cicla default↔custom), `action` (ejecuta).

Items condicionales:
- `custom_color_*` solo si tema = "custom".
- `sonido_modo`, `sonido_archivo`, `sonido_custom_path` solo si sonido = ON.
- `sonido_archivo` solo si modo "default"; `sonido_custom_path` solo si modo "custom".

---

## 6. Overlays compartidos

### Alert overlay (modal)
- Bloquea todo el input.
- Parpadeo entre 2 color pairs.
- `Space`/`Enter` cierra (ejecuta acción de `alarm_ref` si existe). `Esc` cierra.
- `p` pospone (solo si `posponable=True`).
- Audio en loop hasta cerrar (respeta config de sonido).
- Micro: texto centrado sin marco, parpadeando.

### Help overlay (`?`)
- Muestra teclas de la vista actual + globales. Cualquier tecla lo cierra.
- Fondo invertido para distinguirlo. No se muestra en micro.

### File browser
- Navegación `↑↓` + `Enter`. `Esc` sube un nivel (o cierra en raíz).
- Modo `sound`: filtra por `.wav/.oga/.ogg/.mp3`. Modo `restore`: filtra por `.json`.
- No se muestra en micro.

### Log viewer
- Lista de errores con timestamp. `↑↓` navegar, `Esc`/`Enter` cerrar.
- Al abrirlo marca todos como vistos. No se muestra en micro.

---

## 7. Servicios de fondo

### Clima (`services/weather.py`)
Thread background con loop de fetch. Cache en memoria + persistencia (`weather_cache` en data.json). Reintentos (`clima_retry_max`, `clima_retry_segs`), intervalo configurable (`clima_intervalo_min`), fuerza refresh con `u`. API: wttr.in con `%l:+%t`.

### Audio (`services/audio.py`)
Fallback chain: `ffplay` → `paplay` → `aplay` → `curses.beep()` → `\a` stderr. Subprocess no-bloqueante. Loop mientras el Alert está activo. Respeta config de sonido. Carpeta: `~/.config/clock/sounds/`.

### Persistencia (`core/store.py`)
JSON en `~/.config/clock/data.json`. Thread-safe con `threading.Lock`. Escritura atómica (temp + `os.replace`). Version `7`. Carga al iniciar, guarda en cada mutación. **Migración automática:** si existe `clock_data.json` v6 (formato anterior), migrar a `data.json` v7 al iniciar. Backup/restore en `services/backup.py`.

---

## 8. Comportamiento de fondo

### Timers (`_tick_timers`)
Cada tick (50ms) resta elapsed si está activo. Al llegar a 0: desactiva, dispara Alert con `alarm_ref=t`. Al cerrar alerta: resetea al tiempo original.

### Alarmas (`_check_alarms`)
Cada tick compara hora+minuto con alarmas activadas. Match + día OK → Alert, marca "disparada". Con `repeat_days` vuelve a "activado" al minuto siguiente; sin ellos pasa a "desactivado".

### Snoozes (`_check_snoozes`)
Lista de pospuestas con hora+minuto. Al llegar → Alert. Se eliminan al dispararse.

### ToDo alarms (`_tick_todo_alarms`)
Cada tick compara recordatorios de tareas. Match (repetición semanal o fecha exacta) → Alert. Marca `_disparada=True` para no re-disparar en el mismo minuto.

### Global pause/play (`Esc`)
En modo normal: pausa/reanuda timers y crono. No afecta alarmas. Estado en `_global_paused`.

---

## 9. Persistencia: estructura de datos (v7)

```json
{
  "version": 7,
  "alarms": [
    {
      "tipo": "alarma",
      "hora": 15,
      "minutos": 0,
      "segundos": 0,
      "status": "activado",
      "nombre": "Reunión",
      "repeat_days": [0, 1, 2, 3, 4]
    }
  ],
  "timers": [
    { "name": "Timer1", "time": [0, 10, 0] }
  ],
  "todos": [
    {
      "id": 1,
      "tipo": "tarea",
      "orden": 1,
      "texto": "Comprar leche",
      "activo": true,
      "last_done_date": null,
      "recordarme": true,
      "alarma_hora": 7,
      "alarma_min": 0,
      "alarma_dia": 16,
      "alarma_mes": 6,
      "alarma_anio": 2025,
      "repeat_days": [0, 1, 2, 3, 4],
      "created_at": 1750000000
    }
  ],
  "config": {
    "mostrar_marco": true,
    "mostrar_helpers": true,
    "mostrar_segundos": true,
    "formato_24h": true,
    "sonido": true,
    "sonido_modo": "default",
    "sonido_archivo": null,
    "sonido_custom_path": null,
    "clima_activo": false,
    "clima_ubicacion": "",
    "clima_formato": "compacto",
    "clima_intervalo_min": 60,
    "clima_mostrar_hace": true,
    "clima_retry_max": 3,
    "clima_retry_segs": 60,
    "tema": "clasico",
    "alarma_posponer_min": 5,
    "badge_modo": "inline",
    "wc_mostrar": "ver",
    "alarmas_mostrar": "ver",
    "world_clocks": []
  },
  "weather_cache": {
    "text": "Buenos Aires: +12°C",
    "ok": true,
    "ts": 1750000000
  }
}
```

**Nota:** No hay `pomodoro` en v7 (D3). Si un archivo viejo lo trae, se ignora al migrar.

---

## 10. Fases de implementación

| Fase | Contenido | Riesgo |
|---|---|---|
| **1** | Utilidades puras (`time_utils`, `recurrence`, `world_zones`) | Bajo |
| **2** | Servicios (`store` v7+migración, `theme`, `log`, `weather`, `audio`, `backup`) | Medio |
| **3** | UI toolkit (`responsive` 2 tiers, `frame`, `overlay`, `browser`) | Medio |
| **4** | Features MVC: stopwatch → timers → alarms → clock → dashboard → todo → config | Alto |
| **5** | Main app (`app.py`, `router.py`) | Alto |
| **6** | Tests + validación manual | Bajo |

Orden de features por complejidad: stopwatch (más simple, valida el patrón), timers, alarms, clock, dashboard, todo, config. Cada fase se valida antes de la siguiente.

---

## 11. Open items (no bloqueantes)

| # | Item | Prioridad |
|---|---|---|
| O1 | Migrar clima de wttr.in a Open-Meteo | Baja (post-v1) |
| O3 | Badge de actividad en modo micro | Baja |
