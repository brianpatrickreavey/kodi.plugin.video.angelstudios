"""Kodi is started only when it is closed, and only that instance is quit."""

import signal

import pytest

from kodi_app import KodiApp, udp_local_token, udp_table_has_listener


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class _Proc:
    def __init__(self, pid: int = 100) -> None:
        self.pid = pid
        self.returncode = None

    def poll(self):
        return self.returncode


def _app(pids, port_open, popen=None, send=None, killpg=None, kill=None):
    clock = _Clock()
    return KodiApp(
        popen=popen,
        pids=pids,
        port_open=port_open,
        send=send,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
        killpg=killpg if killpg is not None else (lambda _pid, _sig: None),
        kill=kill if kill is not None else (lambda _pid, _sig: None),
    )


def test_udp_token_matches_proc_net_udp():
    assert udp_local_token("127.0.0.1", 9777) == "0100007F:2631"
    table = "   46: 0100007F:2631 00000000:0000 07 00000000:00000000 00:00000000 00000000 0 0 1 2 0\n"
    assert udp_table_has_listener(table, "127.0.0.1", 9777) is True
    assert udp_table_has_listener(table, "127.0.0.1", 1) is False
    wildcard = "   12: 00000000:2631 00000000:0000 07 00000000:00000000 00:00000000 00000000 0 0 1 2 0\n"
    assert udp_table_has_listener(wildcard, "127.0.0.1", 9777) is True


def test_existing_kodi_is_left_open():
    opened = []
    sent = []

    def popen(_binary):
        opened.append(_binary)
        return _Proc()

    app = _app(pids=lambda: [9], port_open=lambda: True, popen=popen, send=sent.append)
    app.open_for_test()
    app.close_if_opened()
    assert opened == []
    assert sent == []
    assert app.started_by_us is False


def test_closed_kodi_is_started_and_then_quit():
    state = {"pids": [], "port": False}
    sent = []
    proc = _Proc()

    def popen(binary):
        assert binary == "/usr/bin/kodi"
        state["pids"] = [proc.pid]
        state["port"] = True
        return proc

    def send(builtin):
        sent.append(builtin)
        state["pids"] = []
        proc.returncode = 0

    app = _app(
        pids=lambda: list(state["pids"]),
        port_open=lambda: state["port"],
        popen=popen,
        send=send,
    )
    app.open_for_test()
    assert app.started_by_us is True
    app.close_if_opened()
    app.close_if_opened()
    assert sent == ["Quit"]
    assert app.started_by_us is False


def test_quit_that_does_not_exit_is_followed_by_sigterm():
    state = {"pids": []}
    killed = []
    proc = _Proc()

    def popen(_binary):
        state["pids"] = [proc.pid]
        return proc

    def killpg(pid, sig):
        killed.append((pid, sig))
        if sig == signal.SIGTERM:
            state["pids"] = []
            proc.returncode = -signal.SIGTERM

    app = _app(
        pids=lambda: list(state["pids"]),
        port_open=lambda: True,
        popen=popen,
        send=lambda _builtin: None,
        killpg=killpg,
    )
    app.open_for_test()
    app.close_if_opened()
    assert killed == [(100, signal.SIGTERM)]


def test_sigkill_follows_a_sigterm_that_does_not_exit():
    state = {"pids": []}
    killed = []
    proc = _Proc()

    def popen(_binary):
        state["pids"] = [proc.pid]
        return proc

    def killpg(_pid, sig):
        killed.append(sig)
        if sig == signal.SIGKILL:
            state["pids"] = []
            proc.returncode = -signal.SIGKILL

    app = _app(
        pids=lambda: list(state["pids"]),
        port_open=lambda: True,
        popen=popen,
        send=lambda _builtin: None,
        killpg=killpg,
    )
    app.open_for_test()
    app.close_if_opened()
    assert killed == [signal.SIGTERM, signal.SIGKILL]


def test_a_replacement_kodi_is_not_signaled():
    killed = []
    proc = _Proc()
    proc.returncode = 0

    app = _app(
        pids=lambda: [999],
        port_open=lambda: True,
        popen=lambda _binary: proc,
        kill=lambda pid, sig: killed.append((pid, sig)),
        killpg=lambda pid, sig: killed.append((pid, sig)),
    )
    app._proc = proc
    app.started_by_us = True
    app.close_if_opened()
    assert killed == []


def test_early_exit_does_not_send_quit():
    sent = []
    proc = _Proc()
    proc.returncode = 1

    app = _app(
        pids=lambda: [],
        port_open=lambda: False,
        popen=lambda _binary: proc,
        send=sent.append,
    )
    with pytest.raises(RuntimeError, match="exited before"):
        app.open_for_test()
    assert sent == []


def test_port_timeout_quits_the_kodi_this_run_started():
    state = {"pids": []}
    sent = []
    proc = _Proc()

    def popen(_binary):
        state["pids"] = [proc.pid]
        return proc

    def send(builtin):
        sent.append(builtin)
        state["pids"] = []
        proc.returncode = 0

    app = _app(
        pids=lambda: list(state["pids"]),
        port_open=lambda: False,
        popen=popen,
        send=send,
    )
    with pytest.raises(RuntimeError, match="127.0.0.1:9777"):
        app.open_for_test()
    assert sent == ["Quit"]
