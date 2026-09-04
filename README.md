# clock

Dashboard TUI en curses para la terminal: reloj, clima, alarmas, temporizadores, cronómetro, tareas y configuración. En Python puro (solo stdlib), instalable y actualizable en una línea.

## Instalar

```bash
curl -fsSL https://raw.githubusercontent.com/braiidev/clock/main/install.sh | bash
```

Instala sin sudo: código en `~/.local/share/clock-tui/`, comando `clock` en `~/.local/bin/clock`. Los datos personales quedan en `~/.config/clock/` y no se tocan.

## Usar

```bash
clock
```

| Tecla | Acción |
|---|---|
| `0`–`6` | Saltar a vista (Dash, Reloj, Alarmas, Timers, Crono, ToDo, Config) |
| `[` `]` | Ciclar vistas |
| `a` `e` `d` | Añadir / Editar / Borrar (con confirmación) |
| `Space` | Toggle on/off, play/pause, done/undone |
| `?` | Ayuda contextual |
| `q` | Salir (guarda todo) |

## Actualizar

```bash
clock --update          # actualiza (git pull; corre historial si diverge)
clock --check-update    # consulta si hay versión nueva
# o dentro de la TUI: Config → Sistema → Comprobar actualización
```

Al entrar, clock verifica en background y avisa con un toast si hay una versión nueva. Para desactivarlo: `CLOCK_NO_AUTO_UPDATE=1 clock`.

## Desinstalar

```bash
clock --uninstall       # pide confirmación (y si querés borrar también los datos)
```

## Comandos

```bash
clock                   # TUI
clock --update          # actualizar
clock --check-update    # verificar versión
clock --uninstall       # desinstalar
clock --version         # versión instalada (1.1.0)
```

## Datos

| Qué | Dónde |
|---|---|
| Alarmas, timers, tareas, config | `~/.config/clock/data.json` |
| Log de errores | `~/.config/clock/clock_error.log` |
| Sonidos custom | `~/.config/clock/sounds/` |
| Versión de datos | v7 (migración automática desde el formato viejo) |

Requiere **Python ≥ 3.9** y `git` solo para instalar/actualizar.