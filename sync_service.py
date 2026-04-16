"""Background sync service — queries NTP servers and sets system time."""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable, List, Optional

from ntp_client import NTPResult, query_all, median_offset as calc_median
from time_setter import apply_offset

log = logging.getLogger(__name__)


class SyncService:
    """
    Runs a background thread that periodically:
      1. Queries all configured NTP servers concurrently.
      2. Computes the median offset.
      3. Calls SetSystemTimeAsFileTime (Windows, requires admin).

    Callbacks are invoked from the background thread — callers must
    marshal GUI updates to the main thread (e.g. via root.after).
    """

    def __init__(self, config) -> None:
        self.config = config

        self._thread: Optional[threading.Thread] = None
        self._stop_evt  = threading.Event()
        self._now_evt   = threading.Event()   # set to trigger immediate sync
        self._lock      = threading.Lock()    # guards _running flag

        # ── Public callbacks ─────────────────────────────────────────────────
        self.on_sync_start: Optional[Callable[[], None]] = None
        self.on_sync_done: Optional[
            Callable[[List[NTPResult], Optional[float], bool, str], None]
        ] = None
        self.on_tick: Optional[Callable[[int], None]] = None  # remaining seconds

        # ── State readable from GUI thread ───────────────────────────────────
        self.last_results: List[NTPResult] = []
        self.last_offset: Optional[float] = None
        self.last_sync_ts: Optional[float] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_evt.clear()
            self._thread = threading.Thread(
                target=self._loop, daemon=True, name="SyncService"
            )
            self._thread.start()

    def stop(self) -> None:
        self._stop_evt.set()
        self._now_evt.set()   # unblock any wait

    def trigger(self) -> None:
        """Request an immediate sync regardless of the remaining interval."""
        if self._thread and self._thread.is_alive():
            self._now_evt.set()
        else:
            # Service not running — fire a one-shot sync thread
            threading.Thread(
                target=self._do_sync, daemon=True, name="ManualSync"
            ).start()

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    # ── Internal loop ─────────────────────────────────────────────────────────
    def _loop(self) -> None:
        while not self._stop_evt.is_set():
            self._do_sync()
            if self._stop_evt.is_set():
                break
            self._wait_interval()

    def _wait_interval(self) -> None:
        """Wait for sync_interval seconds, ticking every second, or until
        _now_evt / _stop_evt fires."""
        interval = self.config.sync_interval
        elapsed = 0
        self._now_evt.clear()
        while elapsed < interval and not self._stop_evt.is_set():
            if self._now_evt.wait(timeout=1.0):
                self._now_evt.clear()
                break
            elapsed += 1
            if self.on_tick and not self._stop_evt.is_set():
                self.on_tick(interval - elapsed)

    def _do_sync(self) -> None:
        if self.on_sync_start:
            try:
                self.on_sync_start()
            except Exception:
                pass

        results: List[NTPResult] = []
        offset: Optional[float] = None
        success = False
        msg = "No valid NTP responses"

        try:
            results = query_all(self.config.servers, timeout=self.config.timeout)
            offset = calc_median(results)

            if offset is not None:
                success, msg = apply_offset(offset)
            else:
                msg = "No usable NTP response (all servers failed or bad stratum)"

            self.last_results = results
            self.last_offset  = offset
            self.last_sync_ts = time.time()

        except Exception as exc:
            log.exception("Sync error")
            msg = f"Unexpected error: {exc}"

        if self.on_sync_done:
            try:
                self.on_sync_done(results, offset, success, msg)
            except Exception:
                pass
