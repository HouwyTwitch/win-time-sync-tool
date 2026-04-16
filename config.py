"""Configuration and NTP server catalog."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List

CONFIG_PATH = Path.home() / ".ntp_time_sync" / "config.json"

# ---------------------------------------------------------------------------
# Full NTP server catalog organized by provider
# ---------------------------------------------------------------------------
SERVER_CATALOG: dict[str, list[str]] = {
    "NTP Pool (Global)": [
        "pool.ntp.org",
        "0.pool.ntp.org", "1.pool.ntp.org", "2.pool.ntp.org", "3.pool.ntp.org",
    ],
    "NTP Pool (Europe)": [
        "europe.pool.ntp.org",
        "0.europe.pool.ntp.org", "1.europe.pool.ntp.org",
        "2.europe.pool.ntp.org", "3.europe.pool.ntp.org",
    ],
    "NTP Pool (Asia)": [
        "asia.pool.ntp.org",
        "0.asia.pool.ntp.org", "1.asia.pool.ntp.org",
        "2.asia.pool.ntp.org", "3.asia.pool.ntp.org",
    ],
    "NTP Pool (North America)": [
        "north-america.pool.ntp.org",
        "0.north-america.pool.ntp.org", "1.north-america.pool.ntp.org",
        "2.north-america.pool.ntp.org", "3.north-america.pool.ntp.org",
    ],
    "NTP Pool (Russia)": [
        "ru.pool.ntp.org",
        "0.ru.pool.ntp.org", "1.ru.pool.ntp.org",
        "2.ru.pool.ntp.org", "3.ru.pool.ntp.org",
    ],
    "Google Public NTP": [
        "time.google.com",
        "time1.google.com", "time2.google.com",
        "time3.google.com", "time4.google.com",
        "time.android.com",
    ],
    "Cloudflare NTP": [
        "time.cloudflare.com",
    ],
    "Amazon AWS": [
        "time.aws.com",
        "amazon.pool.ntp.org",
        "0.amazon.pool.ntp.org", "1.amazon.pool.ntp.org",
        "2.amazon.pool.ntp.org", "3.amazon.pool.ntp.org",
    ],
    "Microsoft": [
        "time.windows.com",
    ],
    "Apple": [
        "time.apple.com",
        "time-macos.apple.com", "time-ios.apple.com",
        "time1.apple.com", "time2.apple.com", "time3.apple.com",
        "time4.apple.com", "time5.apple.com", "time6.apple.com",
        "time7.apple.com", "time.euro.apple.com",
    ],
    "Facebook": [
        "time.facebook.com",
        "time1.facebook.com", "time2.facebook.com",
        "time3.facebook.com", "time4.facebook.com", "time5.facebook.com",
    ],
    "NIST (USA)": [
        "time.nist.gov",
        "time-a-g.nist.gov", "time-b-g.nist.gov",
        "time-c-g.nist.gov", "time-d-g.nist.gov", "time-e-g.nist.gov",
        "time-a-wwv.nist.gov", "time-b-wwv.nist.gov",
        "time-c-wwv.nist.gov", "time-d-wwv.nist.gov", "time-e-wwv.nist.gov",
        "time-a-b.nist.gov", "time-b-b.nist.gov",
        "time-c-b.nist.gov", "time-d-b.nist.gov", "time-e-b.nist.gov",
        "time-nw.nist.gov",
        "utcnist.colorado.edu", "utcnist2.colorado.edu",
    ],
    "USNO (US Navy)": [
        "tick.usno.navy.mil", "tock.usno.navy.mil", "ntp2.usno.navy.mil",
    ],
    "HE.net": [
        "clock.sjc.he.net", "clock.fmt.he.net", "clock.nyc.he.net",
    ],
    "VNIIFTRI (Russia)": [
        "ntp1.vniiftri.ru", "ntp2.vniiftri.ru",
        "ntp3.vniiftri.ru", "ntp4.vniiftri.ru",
        "ntp.sstf.nsk.ru",
        "ntp1.niiftri.irkutsk.ru", "ntp2.niiftri.irkutsk.ru",
        "vniiftri.khv.ru", "vniiftri2.khv.ru",
        "ntp21.vniiftri.ru",
        "ntp.mobatime.ru",
    ],
    "MSK-IX (Russia)": [
        "ntp.ix.ru",
    ],
    "Stratum1.ru": [
        "ntp1.stratum1.ru", "ntp2.stratum1.ru", "ntp3.stratum1.ru",
        "ntp4.stratum1.ru", "ntp5.stratum1.ru",
    ],
    "Stratum2.ru": [
        "ntp1.stratum2.ru", "ntp2.stratum2.ru", "ntp3.stratum2.ru",
        "ntp4.stratum2.ru", "ntp5.stratum2.ru",
    ],
    "NTP-Servers.net": [
        "ntp0.ntp-servers.net", "ntp1.ntp-servers.net", "ntp2.ntp-servers.net",
        "ntp3.ntp-servers.net", "ntp4.ntp-servers.net", "ntp5.ntp-servers.net",
        "ntp6.ntp-servers.net", "ntp7.ntp-servers.net",
    ],
    "time.in.ua (Ukraine)": [
        "ntp.time.in.ua", "ntp2.time.in.ua", "ntp3.time.in.ua",
    ],
    "Netnod (Sweden)": [
        "ntp.se",
        "gbg1.ntp.se", "gbg2.ntp.se",
        "mmo1.ntp.se", "mmo2.ntp.se",
        "sth1.ntp.se", "sth2.ntp.se",
        "svl1.ntp.se", "svl2.ntp.se",
    ],
    "Hetzner (Germany)": [
        "ntp1.hetzner.de", "ntp2.hetzner.de", "ntp3.hetzner.de",
    ],
    "PTB (Germany)": [
        "ptbtime1.ptb.de", "ptbtime2.ptb.de",
    ],
    "RIPE NCC": [
        "ntp.ripe.net",
    ],
    "Internet Systems Consortium": [
        "clock.isc.org",
    ],
    "TimeNL / SIDN": [
        "ntp.time.nl",
    ],
    "NICT (Japan)": [
        "ntp.nict.jp",
    ],
    "NTT (Japan)": [
        "x.ns.gin.ntt.net", "y.ns.gin.ntt.net",
    ],
    "MFEED (Japan)": [
        "ntp1.jst.mfeed.ad.jp", "ntp2.jst.mfeed.ad.jp", "ntp3.jst.mfeed.ad.jp",
    ],
    "Chinese Academy of Sciences": [
        "ntp.ntsc.ac.cn",
    ],
    "Trabia Network": [
        "time-a.as43289.net", "time-b.as43289.net", "time-c.as43289.net",
    ],
    "QiX / YYCIX (Canada)": [
        "ntp.qix.ca", "ntp1.qix.ca", "ntp2.qix.ca", "ntp.yycix.ca",
    ],
    "ACO.net (Austria)": [
        "ts1.aco.net", "ts2.aco.net",
    ],
    "AS34288 (Switzerland)": [
        "ntp0.as34288.net", "ntp1.as34288.net",
    ],
    "TRC Fiord (Russia)": [
        "ntp.fiord.ru",
    ],
    "NRC (Canada)": [
        "time.nrc.ca",
    ],
    "Universities (Russia)": [
        "ntp.nsu.ru", "ntp.psn.ru", "ntp.rsu.edu.ru",
    ],
    "Universities (USA)": [
        "ntp1.net.berkeley.edu", "ntp2.net.berkeley.edu",
        "ntp.gsu.edu", "tick.usask.ca", "tock.usask.ca",
        "timekeeper.isi.edu", "rackety.udel.edu", "mizbeaver.udel.edu",
        "otc1.psu.edu", "navobs1.gatech.edu", "navobs1.wustl.edu",
        "tick.ucla.edu", "tick.uh.edu",
    ],
    "Universities (Europe)": [
        "time.fu-berlin.de", "ntps1-0.cs.tu-berlin.de", "ntps1-1.cs.tu-berlin.de",
        "ntps1-0.uni-erlangen.de", "ntps1-1.uni-erlangen.de",
        "ntp1.fau.de", "ntp2.fau.de",
        "ntp.nic.cz", "time.ufe.cz",
        "ntp.fizyka.umk.pl",
        "tempus1.gum.gov.pl", "tempus2.gum.gov.pl",
        "timehost.lysator.liu.se",
        "ntp1.inrim.it", "ntp2.inrim.it",
        "ntp1.oma.be", "ntp2.oma.be",
        "ntp.atomki.mta.hu",
        "hora.roa.es", "minuto.roa.es",
    ],
    "Other Public Servers": [
        "ntp.nat.ms",
        "ntp.ru",
        "clock.isc.org",
        "ntp.your.org",
        "ntp.mrow.org",
        "ntp.quintex.com",
        "t2.timegps.net",
        "time.esa.int",
    ],
}

DEFAULT_SERVERS: list[str] = [
    "pool.ntp.org",
    "time.google.com",
    "time.cloudflare.com",
    "time.windows.com",
    "time.apple.com",
]


@dataclass
class Config:
    servers: List[str] = field(default_factory=lambda: list(DEFAULT_SERVERS))
    sync_interval: int = 300          # seconds between auto-syncs
    auto_sync: bool = True
    minimize_to_tray: bool = True
    theme: str = "dark"
    timeout: float = 3.0             # per-server NTP query timeout (seconds)
    max_log_lines: int = 300

    # ── persistence ──────────────────────────────────────────────────────────
    def save(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    @classmethod
    def load(cls) -> "Config":
        try:
            if CONFIG_PATH.exists():
                data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                valid = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
                return cls(**valid)
        except Exception:
            pass
        return cls()
