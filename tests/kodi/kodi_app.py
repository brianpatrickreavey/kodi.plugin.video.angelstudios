"""Start Kodi for a test, then quit it only if this run opened it.

An already open Kodi is used as it is and left open. A second Kodi is not started.
"""

import os
import signal
import socket
import struct
import subprocess
import time
from pathlib import Path
from typing import Callable, List, Optional, TextIO

from event_client import send_builtin

KODI_BINARY = "/usr/bin/kodi"
EVENT_HOST = "127.0.0.1"
EVENT_PORT = 9777
START_LOG = "/tmp/script.angelstudios.kodi-start.log"
_READY_SECONDS = 90
_SETTLE_SECONDS = 1
_QUIT_SECONDS = 20
_POLL_SECONDS = 0.2


def udp_local_token(host: str, port: int) -> str:
    """Return the local_address field used by /proc/net/udp."""
    address = struct.unpack("<I", socket.inet_aton(host))[0]
    return f"{address:08X}:{port:04X}"


def udp_table_has_listener(table: str, host: str, port: int) -> bool:
    """Return True when a /proc/net/udp table has this local listener."""
    token = udp_local_token(host, port)
    for line in table.splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[1].upper() == token:
            return True
    return False


def event_port_open(port: int = EVENT_PORT, host: str = EVENT_HOST) -> bool:
    """Return True when Kodi's event server is bound on this machine."""
    try:
        table = Path("/proc/net/udp").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return udp_table_has_listener(table, host, port)


def kodi_bin_pids() -> List[int]:
    """Return pids whose process name is kodi.bin."""
    found = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            name = (entry / "comm").read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if name == "kodi.bin":
            found.append(int(entry.name))
    return found


class KodiApp:
    """One Kodi window for the tests in this pytest session."""

    def __init__(
        self,
        popen: Optional[Callable[[str], "_Process"]] = None,
        pids: Optional[Callable[[], List[int]]] = None,
        port_open: Optional[Callable[[], bool]] = None,
        send: Optional[Callable[[str], None]] = None,
        sleep: Optional[Callable[[float], None]] = None,
        monotonic: Optional[Callable[[], float]] = None,
        killpg: Optional[Callable[[int, int], None]] = None,
        kill: Optional[Callable[[int, int], None]] = None,
        binary: str = KODI_BINARY,
    ) -> None:
        self._popen = popen if popen is not None else self._default_popen
        self._pids = pids if pids is not None else kodi_bin_pids
        self._port_open = port_open if port_open is not None else event_port_open
        self._send = send if send is not None else send_builtin
        self._sleep = sleep if sleep is not None else time.sleep
        self._monotonic = monotonic if monotonic is not None else time.monotonic
        self._killpg = killpg if killpg is not None else os.killpg
        self._kill = kill if kill is not None else os.kill
        self._binary = binary
        self.started_by_us = False
        self._proc: Optional["_Process"] = None
        self._log: Optional[TextIO] = None

    def open_for_test(self) -> None:
        """Use the open Kodi, or start one and wait until port 9777 is listening."""
        if not self._pids():
            self._proc = self._popen(self._binary)
            self.started_by_us = True
        try:
            self._wait_until_ready()
        except Exception:
            self.close_if_opened()
            raise

    def close_if_opened(self) -> None:
        """Quit Kodi only when this run started it."""
        if not self.started_by_us:
            return
        self.started_by_us = False
        try:
            if self._gone():
                return
            self._request_quit()
            if self._wait_until_gone(_QUIT_SECONDS):
                return
            self._signal(signal.SIGTERM)
            if self._wait_until_gone(5):
                return
            self._signal(signal.SIGKILL)
            self._wait_until_gone(5)
        finally:
            self._close_log()

    def _wait_until_ready(self) -> None:
        deadline = self._monotonic() + _READY_SECONDS
        while self._monotonic() < deadline:
            if self._exited_early():
                raise RuntimeError("Kodi exited before it was listening on port 9777." + self._tail_suffix())
            if self._pids() and self._port_open():
                self._sleep(_SETTLE_SECONDS)
                if self._pids() and self._port_open():
                    return
                continue
            self._sleep(_POLL_SECONDS)
        raise RuntimeError("Kodi did not open the event server on 127.0.0.1:9777." + self._tail_suffix())

    def _exited_early(self) -> bool:
        return self.started_by_us and self._proc is not None and self._proc.poll() is not None

    def _request_quit(self) -> None:
        try:
            self._send("Quit")
        except OSError:
            return

    def _wait_until_gone(self, seconds: float) -> bool:
        deadline = self._monotonic() + seconds
        while self._monotonic() < deadline:
            if self._gone():
                return True
            self._sleep(_POLL_SECONDS)
        return self._gone()

    def _gone(self) -> bool:
        if self._pids():
            return False
        return self._proc is None or self._proc.poll() is not None

    def _signal(self, sig: int) -> None:
        pid = 0 if self._proc is None else self._proc.pid
        if pid:
            try:
                self._killpg(pid, sig)
            except OSError:
                pass
        for child in list(self._pids()):
            try:
                self._kill(child, sig)
            except OSError:
                pass

    def _default_popen(self, binary: str) -> "_Process":
        self._log = open(START_LOG, "wb")
        return subprocess.Popen(
            [binary],
            stdin=subprocess.DEVNULL,
            stdout=self._log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    def _close_log(self) -> None:
        if self._log is None:
            return
        self._log.close()
        self._log = None

    def _tail_suffix(self) -> str:
        if self._log is None:
            return ""
        self._log.flush()
        try:
            lines = Path(START_LOG).read_text(encoding="utf-8", errors="replace").splitlines()[-20:]
        except OSError:
            return ""
        if not lines:
            return ""
        return "\n" + "\n".join(lines)


class _Process:
    """The process methods this module uses. subprocess.Popen provides them."""

    pid: int

    def poll(self) -> Optional[int]:
        """Return the exit code, or None while the process is running."""
        raise NotImplementedError
