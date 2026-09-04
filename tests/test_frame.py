"""Tests para ui.responsive y ui.frame (parte pura)."""

from clock_tui.ui.frame import display_width, truncate_ellipsis
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
