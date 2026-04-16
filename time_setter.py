"""Windows system-time setter with microsecond precision via FILETIME API."""
from __future__ import annotations

import sys
import time
from typing import Tuple


def is_windows() -> bool:
    return sys.platform == "win32"


def is_admin() -> bool:
    if not is_windows():
        return False
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin() -> None:
    """Re-launch the current process with UAC elevation (Windows only)."""
    if not is_windows():
        return
    import ctypes
    import subprocess
    params = " ".join(f'"{a}"' for a in sys.argv)
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, params, None, 1
    )


def apply_offset(offset_seconds: float) -> Tuple[bool, str]:
    """
    Apply a clock correction to the Windows system clock.

    Uses SetSystemTimeAsFileTime for 100-nanosecond (sub-microsecond) precision.
    The offset is the NTP-computed difference:
        offset > 0  →  system clock is behind true time  →  we advance it
        offset < 0  →  system clock is ahead             →  we retard it

    Returns (success, message).
    """
    if not is_windows():
        return False, "Time sync is Windows-only (display/query still works)"

    if not is_admin():
        return False, "Administrator privileges required to set system time"

    import ctypes
    import ctypes.wintypes

    # ── 1. Compute corrected UTC timestamp ──────────────────────────────────
    # time.time() returns UTC seconds since Unix epoch as a float.
    # ntplib offset is seconds to ADD to get correct time.
    corrected_unix = time.time() + offset_seconds

    # ── 2. Convert to microseconds, then to 100-ns FILETIME intervals ───────
    # Rounding to the nearest microsecond keeps us within the precision of the
    # float64 representation of a 2026-era Unix timestamp (~0.24 µs resolution).
    corrected_us: int = round(corrected_unix * 1_000_000)   # integer µs
    corrected_100ns: int = corrected_us * 10                 # integer 100-ns

    # ── 3. Add epoch offset (1601-01-01 → 1970-01-01 in 100-ns intervals) ──
    # 116 444 736 000 000 000  =  (1970 - 1601) years in 100-ns ticks
    EPOCH_DIFF: int = 116_444_736_000_000_000
    ft_val: int = corrected_100ns + EPOCH_DIFF

    # ── 4. Pack into FILETIME structure ─────────────────────────────────────
    class FILETIME(ctypes.Structure):
        _fields_ = [
            ("dwLowDateTime",  ctypes.wintypes.DWORD),
            ("dwHighDateTime", ctypes.wintypes.DWORD),
        ]

    ft = FILETIME(
        ft_val & 0xFFFF_FFFF,
        (ft_val >> 32) & 0xFFFF_FFFF,
    )

    # ── 5. Call kernel API ──────────────────────────────────────────────────
    ok = ctypes.windll.kernel32.SetSystemTimeAsFileTime(ctypes.byref(ft))
    if ok:
        us = int(abs(offset_seconds) * 1_000_000)
        sign = "+" if offset_seconds >= 0 else "-"
        return True, (
            f"System time corrected  "
            f"offset {sign}{us} µs  ({offset_seconds * 1000:+.4f} ms)"
        )

    err = ctypes.windll.kernel32.GetLastError()
    return False, f"SetSystemTimeAsFileTime failed  (WinError {err})"
