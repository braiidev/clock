"""Tests para app.router."""

from clock_tui.app.router import (
    NUM_VIEWS,
    Router,
    VIEW_CLOCK,
    VIEW_CONFIG,
    VIEW_DASHBOARD,
)


def _dispatch(current_view, key):
    """Stub dispatch que devuelve (view, key) para verificar el routing."""
    return ("dispatched", current_view, key)


def test_initial_view_is_dashboard():
    r = Router()
    assert r.view_index() == VIEW_DASHBOARD


def test_number_of_views():
    assert NUM_VIEWS == 7


def test_goto_view():
    r = Router()
    r.goto_view(VIEW_CLOCK)
    assert r.view_index() == VIEW_CLOCK


def test_goto_view_same_no_change():
    r = Router()
    changed = r.goto_view(VIEW_DASHBOARD)
    assert changed is False


def test_goto_view_out_of_range():
    r = Router()
    changed = r.goto_view(99)
    assert changed is False
    assert r.view_index() == VIEW_DASHBOARD


def test_cycle_view_forward():
    r = Router()
    r.cycle_view(1)
    assert r.view_index() == 1


def test_cycle_view_wraps():
    r = Router()
    for _ in range(NUM_VIEWS):
        r.cycle_view(1)
    assert r.view_index() == VIEW_DASHBOARD


def test_cycle_view_backward():
    r = Router()
    r.cycle_view(-1)
    assert r.view_index() == VIEW_CONFIG


def test_q_quits():
    r = Router()
    res = r.route(ord("q"), _dispatch)
    assert res.quit_app is True
    assert res.feature_dispatched is False


def test_question_opens_help():
    r = Router()
    res = r.route(ord("?"), _dispatch)
    assert res.toggle_help is True
    assert r.help_open is True


def test_help_any_key_closes():
    r = Router()
    r.route(ord("?"), _dispatch)
    res = r.route(ord("x"), _dispatch)
    assert res.toggle_help is True
    assert r.help_open is False
    assert res.feature_dispatched is False


def test_help_q_still_quits():
    r = Router()
    r.route(ord("?"), _dispatch)
    res = r.route(ord("q"), _dispatch)
    assert res.quit_app is True


def test_direct_view_access():
    r = Router()
    res = r.route(ord("3"), _dispatch)
    assert res.view_changed is True
    assert r.view_index() == 3


def test_dispatch_delegates():
    r = Router()
    res = r.route(ord("a"), _dispatch)
    assert res.feature_dispatched is True
    assert res.feature_result == ("dispatched", VIEW_DASHBOARD, ord("a"))


def test_dispatch_after_view_change():
    r = Router()
    r.route(ord("1"), _dispatch)
    res = r.route(ord("e"), _dispatch)
    assert res.feature_result == ("dispatched", VIEW_CLOCK, ord("e"))


def test_view_name():
    r = Router()
    assert r.view_name(0) == "Dash"
    assert r.view_name(6) == "Conf"
    assert r.view_name(99) == "?"


def test_o_opens_activity_overlay():
    r = Router()
    r.goto_view(VIEW_CLOCK)
    res = r.route(ord("o"), _dispatch)
    assert res.toggle_activity is True
    assert r.activity_open is True
    assert res.feature_dispatched is False


def test_o_closes_activity_overlay():
    r = Router()
    r.goto_view(VIEW_CLOCK)
    r.route(ord("o"), _dispatch)
    res = r.route(ord("o"), _dispatch)
    assert res.toggle_activity is True
    assert r.activity_open is False


def test_activity_any_key_closes():
    r = Router()
    r.goto_view(VIEW_CLOCK)
    r.route(ord("o"), _dispatch)
    res = r.route(ord("x"), _dispatch)
    assert res.toggle_activity is True
    assert r.activity_open is False
    assert res.feature_dispatched is False


def test_activity_q_still_quits():
    r = Router()
    r.goto_view(VIEW_CLOCK)
    r.route(ord("o"), _dispatch)
    res = r.route(ord("q"), _dispatch)
    assert res.quit_app is True


def test_o_ignored_on_dashboard():
    r = Router()
    res = r.route(ord("o"), _dispatch)
    assert res.toggle_activity is False
    assert r.activity_open is False
    assert res.feature_dispatched is True


def test_capture_dispatches_globals_as_feature_keys():
    """En captura (edición), q/?/o/0-9/[] van a la feature, no a los globales."""
    r = Router()
    for key in (ord("q"), ord("?"), ord("o"), ord("3"), ord("]"), ord("[")):
        res = r.route(key, _dispatch, capture=True)
        assert res.feature_dispatched is True
        assert res.feature_result == ("dispatched", VIEW_DASHBOARD, key)
        assert res.quit_app is False
        assert res.toggle_help is False
        assert res.toggle_activity is False
        assert res.view_changed is False
    assert r.help_open is False
    assert r.activity_open is False
    assert r.view_index() == VIEW_DASHBOARD


def test_capture_keeps_view_unchanged():
    """La tecla de cambio de vista en captura NO navega."""
    r = Router()
    res = r.route(ord("3"), _dispatch, capture=True)
    assert res.view_changed is False
    assert r.view_index() == VIEW_DASHBOARD
