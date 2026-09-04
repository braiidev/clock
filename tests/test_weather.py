"""Tests para services.weather."""

import clock_tui.services.weather as w


def test_wrap_text_weather_with_report():
    assert (
        w.wrap_text_weather("Weather report: Buenos Aires +12C") == "Buenos Aires +12C"
    )


def test_wrap_text_weather_plain():
    assert w.wrap_text_weather("Buenos Aires +12C") == "Buenos Aires +12C"


def test_wrap_text_weather_empty():
    assert w.wrap_text_weather("") == ""


def test_fetch_weather(monkeypatch):
    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b"Weather report: Capital Federal, Argentina +25C"

    class FakeUrl:
        def __init__(self):
            self.last_url = None

        def __call__(self, url, headers=None, **kwargs):
            self.last_url = getattr(url, "full_url", None) or url
            return FakeResp()

    fake = FakeUrl()
    monkeypatch.setattr(w.urllib.request, "urlopen", fake)

    ok, text = w.fetch_weather("Buenos Aires")
    assert ok is True
    assert "Capital Federal" in text
    assert "%l:+%t" in fake.last_url


def test_format_age():
    import time

    assert w.format_age(None) == ""
    assert w.format_age(time.time() - 5) == "hace instantes"
    assert w.format_age(time.time() - 120) == "hace 2 min"
    assert w.format_age(time.time() - 7200) == "hace 2 h"
