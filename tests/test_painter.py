"""Tests del painter y helpers de dibujo con un stdscr falso."""

from clock_tui.ui.frame import Painter, truncate_ellipsis


class FakeStdscr:
    def __init__(self, h=24, w=80):
        self._rows = [[" "] * w for _ in range(h)]
        self._h, self._w = h, w

    def getmaxyx(self):
        return self._h, self._w

    def addstr(self, y, x, s, attr=0):
        if 0 <= y < self._h:
            for i, ch in enumerate(s):
                if 0 <= x + i < self._w:
                    self._rows[y][x + i] = ch

    def erase(self):
        self._rows = [[" "] * self._w for _ in range(self._h)]

    def refresh(self):
        pass

    def line(self, y):
        return "".join(self._rows[y])


def test_painter_safe_out_of_bounds():
    s = FakeStdscr(5, 10)
    p = Painter(s)
    p.safe(99, 0, "x")  # fuera de rango, no debe explotar
    p.safe(0, 99, "x")
    p.safe(0, -1, "x")
    assert s.line(0) == " " * 10


def test_painter_centered():
    s = FakeStdscr(10, 20)
    p = Painter(s)
    p.centered(2, 0, 20, "HOLA", 0)
    assert s.line(2) == " " * 8 + "HOLA" + " " * 8


def test_painter_safe_truncates_right():
    s = FakeStdscr(3, 6)
    p = Painter(s)
    p.safe(0, 0, "abcdefgh")
    assert s.line(0) == "abcde "  # deja al menos 1 columna al borde


def test_truncate_ellipsis_combine():
    assert truncate_ellipsis("1234567890", 5) == "1234…"
