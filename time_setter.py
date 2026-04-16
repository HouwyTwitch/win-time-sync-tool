"""Windows system-time setter with microsecond precision."""
from __future__ import annotations

import ctypes
import ctypes.wintypes
import datetime
import sys
import time
from typing import Tuple


def is_windows() -> bool:
    return sys.platform == "win32"


def is_admin() -> bool:
    if not is_windows():
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin() -> None:
    """Re-launch the current process with UAC elevation (Windows only)."""
    if not is_windows():
        return
    params = " ".join(f'"{a}"' for a in sys.argv)
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, params, None, 1
    )


# ── FILETIME epoch constant ───────────────────────────────────────────────────
# 100-nanosecond intervals between 1601-01-01 and 1970-01-01
_EPOCH_DIFF: int = 116_444_736_000_000_000


def _unix_to_filetime(unix_seconds: float) -> int:
    """Convert a UTC Unix timestamp (float) to a Windows FILETIME integer."""
    us: int = round(unix_seconds * 1_000_000)   # round to nearest µs
    return us * 10 + _EPOCH_DIFF                 # convert to 100-ns ticks


def apply_offset(offset_seconds: float) -> Tuple[bool, str]:
    """
    Apply a clock correction to the Windows system clock.

    Strategy (highest → lowest precision):
      1. NtSetSystemTime  (ntdll.dll)  — 100 ns resolution
      2. SetSystemTime    (kernel32)   — 1 ms  resolution  (fallback)

    The NTP offset semantics:
        offset > 0  →  system clock is behind true time  →  advance it
        offset < 0  →  system clock is ahead             →  retard it

    Returns (success, message).
    """
    if not is_windows():
        return False, "Time sync is Windows-only (display/query still works)"

    if not is_admin():
        return False, "Administrator privileges required to set system time"

    corrected_unix = time.time() + offset_seconds
    ft_val = _unix_to_filetime(corrected_unix)

    # ── Strategy 1: NtSetSystemTime (ntdll) — 100 ns precision ──────────────
    # NtSetSystemTime(NewTime: PLARGE_INTEGER, OldTime: PLARGE_INTEGER | None)
    # NTSTATUS 0 == STATUS_SUCCESS
    try:
        class LARGE_INTEGER(ctypes.Structure):
            _fields_ = [("QuadPart", ctypes.c_longlong)]

        li = LARGE_INTEGER(ft_val)
        status = ctypes.windll.ntdll.NtSetSystemTime(ctypes.byref(li), None)
        if status == 0:
            return True, _success_msg(offset_seconds, precision="100 ns")
        # Non-zero NTSTATUS — fall through to SetSystemTime
    except OSError:
        pass

    # ── Strategy 2: SetSystemTime (kernel32) — 1 ms precision ────────────────
    # Convert FILETIME → calendar fields via FileTimeToSystemTime so we don't
    # have to do the calendar math ourselves.
    class SYSTEMTIME(ctypes.Structure):
        _fields_ = [
            ("wYear",         ctypes.wintypes.WORD),
            ("wMonth",        ctypes.wintypes.WORD),
            ("wDayOfWeek",    ctypes.wintypes.WORD),
            ("wDay",          ctypes.wintypes.WORD),
            ("wHour",         ctypes.wintypes.WORD),
            ("wMinute",       ctypes.wintypes.WORD),
            ("wSecond",       ctypes.wintypes.WORD),
            ("wMilliseconds", ctypes.wintypes.WORD),
        ]

    dt = datetime.datetime.fromtimestamp(corrected_unix, tz=datetime.timezone.utc)
    st = SYSTEMTIME(
        wYear=dt.year, wMonth=dt.month, wDayOfWeek=dt.weekday(),
        wDay=dt.day, wHour=dt.hour, wMinute=dt.minute,
        wSecond=dt.second, wMilliseconds=dt.microsecond // 1000,
    )
    ok = ctypes.windll.kernel32.SetSystemTime(ctypes.byref(st))
    if ok:
        return True, _success_msg(offset_seconds, precision="1 ms")

    err = ctypes.windll.kernel32.GetLastError()
    return False, f"SetSystemTime failed  (WinError {err})"


def _success_msg(offset_seconds: float, precision: str) -> str:
    us   = int(abs(offset_seconds) * 1_000_000)
    sign = "+" if offset_seconds >= 0 else "-"
    return (
        f"System time corrected  "
        f"offset {sign}{us} µs  ({offset_seconds * 1000:+.4f} ms)  "
        f"[precision: {precision}]"
    )
