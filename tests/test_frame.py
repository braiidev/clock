"""Tests para ui.responsive y ui.frame (parte pura)."""

from clock_tui.ui.frame import (
    content_capacity,
    display_width,
    draw_frame,
    scroll_window,
    truncate_ellipsis,
)
from clock_tui.ui.responsive import size_tier


def test_size_tier_micro_solo_altura():
    assert size_tier(2, 100) == "micro"  # h<3 aunque sea muy ancho
    assert size_tier(1, 200) == "micro"
    assert size_tier(2, 20) == "micro"


def test_size_tier_mini_altura_intermedia():
    assert size_tier(3, 30) == "mini"
    assert size_tier(4, 100) == "mini"
    assert size_tier(7, 60) == "mini"


def test_size_tier_full_altura_alta():
    assert size_tier(8, 20) == "full"  # h>=8 aunque sea angosto
    assert size_tier(8, 40) == "full"
    assert size_tier(20, 60) == "full"


def test_display_width_emoji_is_two():
    assert display_width("ab") == 2
    # emoji (0x1F000..0x1FFFF) ocupa 2
    assert display_width("\U0001f600") == 2
    assert display_width("a\U0001f600") == 3


def test_truncate_ellipsis_fits():
    assert truncate_ellipsis("hola", 10) == "hola"


def test_truncate_ellipsis_truncates():
    # "Comprar leche y pan" (20 cols); a 12 cabe "Comprar lec" + "…"
    assert truncate_ellipsis("Comprar leche y pan", 12) == "Comprar lec…"
    assert len(truncate_ellipsis("Comprar leche y pan", 12)) == 12


def test_truncate_ellipsis_short_max():
    # incluso un max muy chico agrega la ellipsis
    assert truncate_ellipsis("abc", 1).endswith("…")


def test_content_capacity_altura():
    assert content_capacity(6, 0) == 1
    assert content_capacity(12, 0) == 6
    assert content_capacity(12, 2) == 3


def test_scroll_window_estable_si_en_rango():
    assert scroll_window(2, 10, 5, 1) == 1


def test_scroll_window_empuja_abajo():
    assert scroll_window(6, 10, 5, 1) == 2


def test_scroll_window_retrocede_arriba():
    assert scroll_window(0, 10, 5, 3) == 0


def test_scroll_window_sin_desborde_es_cero():
    assert scroll_window(3, 4, 12, 0) == 0


class _Rec:
    def __init__(self, h: int, w: int):
        self.h = h
        self.w = w
        self.calls: list[tuple[int, int, str]] = []

    def getmaxyx(self) -> tuple[int, int]:
        return self.h, self.w

    def addstr(self, y: int, x: int, s: object, *a: object) -> None:
        self.calls.append((y, x, str(s)))

    def erase(self) -> None:
        pass

    def refresh(self) -> None:
        pass


def test_draw_frame_no_pisa_footer_y_trunca_con_ellipsis():
    largo = (
        "este texto es suficientemente largo como para no caber y forzar la ellipsis"
    )
    rows = [f"fila {i} {largo}" for i in range(12)]
    scr = _Rec(8, 60)
    draw_frame(scr, "Título", rows, pairs={"marco": 1, "texto": 2, "helpers": 3})

    max_y = max(y for y, x, s in scr.calls if s)
    assert max_y <= scr.h - 2  # la última fila queda libre (footer)

    rows_dibujadas = [s for y, x, s in scr.calls if s.startswith("fila")]
    assert len(rows_dibujadas) == 2  # capacity con h=8 → box de 6, 2 filas
    assert all(r.endswith("…") for r in rows_dibujadas)


def test_draw_frame_bottom_counter_sobre_borde():
    scr = _Rec(24, 60)
    draw_frame(
        scr,
        "Título",
        ["fila A", "fila B"],
        pairs={"marco": 1, "texto": 2, "helpers": 3, "nav": 4},
        bottom_counter="(2/10)",
    )
    coincidencias = [s for y, x, s in scr.calls if s == "(2/10)"]
    assert len(coincidencias) == 1
    y, x, _ = next(c for c in scr.calls if c[2] == "(2/10)")
    # el contador vive en la última fila de contenido del box (borde inferior)
    assert y == 13  # contenido_capacity(24)=18 → box_h=6, sy=8 → borde en 13
    assert x == 47  # alineado a la derecha, antes de la esquina ┘
    # no desplaza filas de contenido
    filas = [s for y2, x2, s in scr.calls if s.startswith("fila")]
    assert "fila A" in filas and "fila B" in filas


def test_draw_frame_bottom_counter_sin_marco_se_omite():
    scr = _Rec(24, 60)
    draw_frame(
        scr,
        "Título",
        ["fila A"],
        pairs={"marco": 1, "texto": 2, "helpers": 3},
        mostrar_marco=False,
        bottom_counter="(1/1)",
    )
    assert not [s for y, x, s in scr.calls if s == "(1/1)"]


def test_draw_frame_mini_estira_y_no_dibuja_helpers():
    scr = _Rec(3, 60)
    draw_frame(
        scr,
        "Título",
        ["fila 0", "fila 1", "fila 2"],
        pairs={"marco": 1, "texto": 2, "helpers": 3},
        helper_lines=["↑↓ navegar"],
    )
    # mini: la caja ocupa toda la pantalla (3 filas) y tiene 1 fila de contenido
    assert max(y for y, x, s in scr.calls if s) <= 2
    assert any("[ Título ]" in s or "Título" in s for y, x, s in scr.calls)
    assert not any(s == "↑↓ navegar" for y, x, s in scr.calls)
    filas = [s for y, x, s in scr.calls if s == "fila 0"]
    assert filas


def test_draw_frame_mini_centra_caja_chica():
    scr = _Rec(7, 60)
    draw_frame(
        scr,
        "Título",
        ["fila A"],
        pairs={"marco": 1, "texto": 2, "helpers": 3},
        helper_lines=["↑↓ navegar"],
    )
    # 1 solo contenido → box_h=5, centrado en h=7 → borde inferior en la fila 5
    assert any(s == "fila A" for y, x, s in scr.calls)
    assert not any(s == "↑↓ navegar" for y, x, s in scr.calls)


def test_draw_frame_full_mantiene_helpers_y_footer():
    scr = _Rec(10, 60)
    draw_frame(
        scr,
        "Título",
        ["fila A"],
        pairs={"marco": 1, "texto": 2, "helpers": 3, "nav": 4},
        helper_lines=["↑↓ navegar"],
        footer="NORMAL",
    )
    assert any(s == "↑↓ navegar" for y, x, s in scr.calls)
    assert any(s == "NORMAL" for y, x, s in scr.calls)
