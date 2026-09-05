"""Tests para ui.responsive y ui.frame (parte pura)."""

from clock_tui.ui.frame import (
    content_capacity,
    display_width,
    draw_frame,
    scroll_window,
    truncate_ellipsis,
)
from clock_tui.ui.responsive import size_tier


def test_size_tier_micro_only_both_small():
    assert size_tier(3, 30) == "micro"  # w<40 AND h<5
    assert size_tier(4, 39) == "micro"


def test_size_tier_full_otherwise():
    assert size_tier(4, 40) == "full"  # w >= 40
    assert size_tier(5, 30) == "full"  # h >= 5
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
