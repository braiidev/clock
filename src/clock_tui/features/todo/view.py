"""Vista del ToDo: rendering puro sobre curses.

3 pantallas: lista, editor, confirmar borrado.
Sin panel lateral (D7, panel `o` eliminado).
"""

from __future__ import annotations

import datetime
from typing import Any

from clock_tui.core.recurrence import DIAS_ABBR
from clock_tui.ui.frame import draw_frame

from .model import TodoModel


def render(
    stdscr: Any,
    model: TodoModel,
    *,
    theme: dict[str, int],
    pairs: dict[str, int],
    config: dict[str, Any],
) -> None:
    mostrar_marco = config.get("mostrar_marco", True)
    mostrar_helpers = config.get("mostrar_helpers", True)
    if model.edit_mode:
        _render_edit(
            stdscr,
            model,
            pairs=pairs,
            mostrar_marco=mostrar_marco,
            mostrar_helpers=mostrar_helpers,
        )
        return
    if model.confirm_delete:
        _render_confirm(stdscr, model, pairs=pairs, mostrar_marco=mostrar_marco)
        return
    _render_list(
        stdscr,
        model,
        pairs=pairs,
        mostrar_marco=mostrar_marco,
        mostrar_helpers=mostrar_helpers,
    )


def _render_list(
    stdscr: Any,
    model: TodoModel,
    *,
    pairs: dict[str, int],
    mostrar_marco: bool,
    mostrar_helpers: bool,
) -> None:
    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    rows = [now_str, ""]

    total = model.count
    if total:
        start, end = model.visible_range()
        visible = model.todos[start:end]
        for i_rel, t in enumerate(visible):
            i_abs = i_rel + start
            sel = "\u25ba" if i_abs == model.selected_idx else " "
            rows.append(f"{sel} {model.item_display(t)}")
        if total > 8:
            shown_end = min(start + 8, total)
            rows.append(f"  ({start + 1}\u2013{shown_end} de {total})")
    else:
        rows.append("Presion\u00e1 <a> para crear")

    helper = (
        [
            "a:nuevo  \u2191\u2191:nav  \u2190\u2192/JK:mover  Space:\u2714/\u25cb  e:editar  d:borrar  x:alarma"
        ]
        if mostrar_helpers
        else []
    )

    draw_frame(
        stdscr,
        "\u25a4 ToDo",
        rows,
        mostrar_marco=mostrar_marco,
        helper_lines=helper,
        pairs=pairs,
    )


def _render_edit(
    stdscr: Any,
    model: TodoModel,
    *,
    pairs: dict[str, int],
    mostrar_marco: bool,
    mostrar_helpers: bool,
) -> None:
    f = model.edit_field
    es_nota = model.temp_tipo == "nota"
    hh, mm, dia, mes, anio = model.temp_alarma

    def fmark(n: int) -> str:
        return "\u25ba" if f == n else " "

    tipo_str = "Tarea" if not es_nota else "Nota"
    rows = [
        f"{fmark(0)} Tipo       : [{tipo_str}]",
        (
            f"{fmark(1)} Texto      : {model.temp_texto}_"
            if f == 1
            else f"{fmark(1)} Texto      : {model.temp_texto}"
        ),
    ]

    if not es_nota:
        rec_str = "\u2714 S\u00ed" if model.temp_recordarme else "\u2718 No"
        rows.append(f"{fmark(2)} Recordarme : [{rec_str}]")

        if model.temp_recordarme:
            rep_str = "\u2714 S\u00ed" if model.temp_repetir else "\u2718 No"
            rows.append(f"{fmark(3)} Repetir    : [{rep_str}]")
            if model.temp_repetir:
                partes_dias: list[str] = []
                for d in range(7):
                    marcado = d in model.temp_days
                    txt = f"[{DIAS_ABBR[d]}]" if marcado else f" {DIAS_ABBR[d]} "
                    if f == 4 and d == model.temp_days_cursor:
                        txt = (
                            f"\u00bb{txt}\u00ab"
                            if marcado
                            else f"\u00bb{DIAS_ABBR[d]}\u00ab"
                        )
                    partes_dias.append(txt)
                rows += [
                    f"{fmark(4)} D\u00edas       : {''.join(partes_dias)}",
                    f"{fmark(5)} Hora       : \u25c4{hh:02d}\u25ba",
                    f"{fmark(6)} Minuto     : \u25c4{mm:02d}\u25ba",
                ]
            else:
                rows += [
                    f"{fmark(4)} Hora       : \u25c4{hh:02d}\u25ba",
                    f"{fmark(5)} Minuto     : \u25c4{mm:02d}\u25ba",
                    f"{fmark(6)} D\u00eda        : \u25c4{dia:02d}\u25ba",
                    f"{fmark(7)} Mes        : \u25c4{mes:02d}\u25ba",
                    f"{fmark(8)} A\u00f1o        : \u25c4{anio}\u25ba",
                ]

    helper_lines = (
        (
            ["\u2191\u2191:l\u00ednea  Enter:guardar  Esc:cancelar"]
            if es_nota
            else [
                "\u2191\u2191:l\u00ednea  Enter:guardar  Esc:cancelar",
                "Tipo/Recordarme/Repetir: Tab o Space  |  Valores/D\u00edas: \u2190\u2192 Space",
            ]
        )
        if mostrar_helpers
        else []
    )

    draw_frame(
        stdscr,
        "\u270e Editar",
        rows,
        mostrar_marco=mostrar_marco,
        helper_lines=helper_lines,
        pairs=pairs,
    )


def _render_confirm(
    stdscr: Any,
    model: TodoModel,
    *,
    pairs: dict[str, int],
    mostrar_marco: bool,
) -> None:
    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    t = model.todos[model.selected_idx] if model.todos else None
    texto = t["texto"][:28] if t else "?"
    rows = [
        now_str,
        "",
        f"\u00bfEliminar '{texto}'?",
        "  y / s / Enter = S\u00ed    cualquier tecla = No",
    ]
    draw_frame(
        stdscr,
        "\u25a4 ToDo",
        rows,
        mostrar_marco=mostrar_marco,
        pairs=pairs,
    )
