"""NTP client — concurrent multi-server querying with microsecond precision."""
from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass
from typing import List, Optional

import ntplib


@dataclass
class NTPResult:
    server: str
    success: bool
    offset: float = 0.0      # clock offset in seconds (+ means system is behind)
    delay: float = 0.0       # round-trip delay in seconds
    stratum: int = 0
    tx_time: float = 0.0     # server transmit timestamp (Unix)
    precision: int = 0       # server clock precision (log2 seconds)
    error: Optional[str] = None

    # ── convenience properties ───────────────────────────────────────────────
    @property
    def offset_us(self) -> float:
        """Offset in microseconds."""
        return self.offset * 1_000_000

    @property
    def offset_ms(self) -> float:
        """Offset in milliseconds."""
        return self.offset * 1_000

    @property
    def delay_ms(self) -> float:
        """Round-trip delay in milliseconds."""
        return self.delay * 1_000

    @property
    def accuracy_ms(self) -> float:
        """Estimated one-way accuracy (half round-trip) in milliseconds."""
        return self.delay_ms / 2


# ---------------------------------------------------------------------------
# Per-server query
# ---------------------------------------------------------------------------

def _query_one(server: str, timeout: float) -> NTPResult:
    try:
        client = ntplib.NTPClient()
        resp = client.request(server, version=4, port=123, timeout=timeout)
        return NTPResult(
            server=server,
            success=True,
            offset=resp.offset,
            delay=resp.delay,
            stratum=resp.stratum,
            tx_time=resp.tx_time,
            precision=resp.precision,
        )
    except ntplib.NTPException as exc:
        return NTPResult(server=server, success=False, error=f"NTP: {exc}")
    except OSError as exc:
        return NTPResult(server=server, success=False, error=f"Network: {exc}")
    except Exception as exc:
        return NTPResult(server=server, success=False, error=str(exc))


# ---------------------------------------------------------------------------
# Concurrent multi-server query
# ---------------------------------------------------------------------------

def query_all(servers: List[str], timeout: float = 3.0) -> List[NTPResult]:
    """Query all servers concurrently. Returns results in original server order."""
    if not servers:
        return []

    n = len(servers)
    results_map: dict[str, NTPResult] = {}

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(n, 32), thread_name_prefix="ntp"
    ) as pool:
        future_to_srv = {pool.submit(_query_one, s, timeout): s for s in servers}
        # Wait a bit longer than the per-server timeout for all futures
        done, _ = concurrent.futures.wait(
            future_to_srv, timeout=timeout + 2
        )
        for f in done:
            srv = future_to_srv[f]
            try:
                results_map[srv] = f.result()
            except Exception as exc:
                results_map[srv] = NTPResult(server=srv, success=False, error=str(exc))

    # Servers that timed out entirely (future never completed)
    for srv in servers:
        if srv not in results_map:
            results_map[srv] = NTPResult(server=srv, success=False, error="Timed out")

    # Return in original order
    return [results_map[s] for s in servers]


# ---------------------------------------------------------------------------
# Median offset calculation
# ---------------------------------------------------------------------------

def median_offset(
    results: List[NTPResult],
    max_stratum: int = 4,
) -> Optional[float]:
    """
    Return the median clock offset (seconds) across valid responses.
    Filters out failed queries and servers with stratum > max_stratum.
    Returns None if no valid responses.
    """
    good = [
        r for r in results
        if r.success and 1 <= r.stratum <= max_stratum
    ]
    if not good:
        return None

    offsets = sorted(r.offset for r in good)
    n = len(offsets)
    if n % 2 == 0:
        return (offsets[n // 2 - 1] + offsets[n // 2]) / 2
    return offsets[n // 2]
