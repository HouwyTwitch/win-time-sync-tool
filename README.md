# NTP Time Sync Tool

A Windows desktop application that synchronises the system clock against multiple NTP servers simultaneously and applies the **median offset** with **microsecond precision**.

---

## Features

- **Multi-server querying** — all configured servers are queried concurrently; the median offset is used, making the result resilient to any single rogue or drifting server
- **Microsecond precision** — offsets displayed in µs; system time written via `SetSystemTimeAsFileTime` (Windows FILETIME, 100 ns resolution)
- **Live clock display** — `HH:MM:SS.ffffff` updated at 30 fps with local timezone
- **Per-server status** — coloured dot (green / amber / red), offset in µs, round-trip time, stratum
- **150+ server catalog** — organised by provider (Google, Cloudflare, Amazon, Apple, Facebook, NIST, USNO, HE.net, VNIIFTRI, MSK-IX, Netnod, PTB, RIPE, ISC, pool.ntp.org regions and more); add/remove with checkboxes
- **Background sync** — configurable auto-sync interval (30 s → 1 h) runs while the window is hidden
- **System tray** — closing the window minimises to tray; right-click for Sync Now / Exit
- **Dark / light theme** toggle; config persisted across sessions

---

## Requirements

| Requirement | Notes |
|---|---|
| Python 3.9+ | Uses `zoneinfo` (stdlib) for timezone display |
| Windows | Time-setting uses the Windows kernel API; NTP querying and the GUI work on any OS |
| Administrator privileges | Required only for writing the corrected time to the OS clock |

---

## Installation

```bash
git clone https://github.com/HouwyTwitch/win-time-sync-tool.git
cd win-time-sync-tool
pip install -r requirements.txt
```

Dependencies installed:

| Package | Purpose |
|---|---|
| `customtkinter` | Modern dark/light GUI widgets |
| `ntplib` | NTP protocol client |
| `pystray` | System-tray icon |
| `Pillow` | Tray icon rendering |

---

## Usage

**Without administrator privileges** — the tool still queries all servers and displays offsets, but cannot write the corrected time to the OS.

**With administrator privileges** — full time correction is applied.

### Option A — right-click → Run as administrator

Right-click `main.py` (or a shortcut to it) and choose *Run as administrator*.

### Option B — elevated command prompt

```bat
:: Open an elevated cmd or PowerShell, then:
python main.py
```

### Option C — Task Scheduler (recommended for auto-start)

1. Open *Task Scheduler* → *Create Task*
2. **General** tab → tick *Run with highest privileges*
3. **Triggers** tab → *At log on*
4. **Actions** tab → `python.exe` with argument `"C:\path\to\main.py"`

---

## Interface overview

```
┌─ ⏱ NTP Time Sync ──────────────────────────── 🔑 Admin  ☀/🌙  ⬛Tray ─┐
│                                                                          │
│  Active Servers          │   14:32:15.847293                             │
│  ──────────────────      │   Wednesday, April 16, 2026                  │
│  🟢 pool.ntp.org         │   UTC+03:00  (MSK)                           │
│     +23.14 µs  12.4 ms S1│                                              │
│  🟢 time.google.com      │  ┌ Offset: +23.14 µs ┬ Accuracy: ±6.2 ms ┬ │
│     +21.80 µs   8.2 ms S1│  │                   │  Servers: 5/5      │ │
│  🟡 time.cloudflare.com  │  └───────────────────┴────────────────────┘ │
│     +45.00 µs  45.1 ms S3│                                              │
│  🟢 time.windows.com     │  [ 🔄  Sync Now                           ]  │
│     +19.30 µs  15.3 ms S1│  Auto-sync  ●  Interval  [ 5 minutes ▼ ]    │
│  🟢 time.apple.com       │  Next sync: 4m 23s                           │
│     +25.10 µs  18.7 ms S1│  Last sync: 14:27:15                         │
│                          │                                              │
│  [ hostname… ] [+]       │                                              │
│  [ Browse Catalog…     ] │                                              │
├──────────────────────────────────────────────────────────────────────────┤
│  Sync Log                                                       [Clear] │
│  [14:27:15.312]  ✓  System time corrected  offset +23 µs (+0.0231 ms)  │
│  [14:22:15.198]  ✓  System time corrected  offset -12 µs (-0.0118 ms)  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## How it works

### 1. Querying

All active servers are queried **concurrently** using a thread pool. Each query uses NTP v4 and records:

- **Offset** — the difference between the server's clock and the local clock (seconds)
- **Round-trip delay** — network latency there and back (seconds)
- **Stratum** — distance from a reference clock (1 = atomic/GPS, 2 = synced to S1, …)

### 2. Median selection

Responses with `stratum > 4` or errors are discarded. The **median offset** of the remaining responses is taken. The median is preferred over the mean because it is unaffected by outliers (a misbehaving server cannot skew the result by more than one rank).

### 3. Applying the correction

```
corrected_UTC = time.time() + median_offset
FILETIME      = round(corrected_UTC × 10⁶) × 10 + 116 444 736 000 000 000
SetSystemTimeAsFileTime(FILETIME)
```

- `time.time()` returns UTC seconds since the Unix epoch as a 64-bit float.  
  At a 2026-era timestamp (~1.74 × 10⁹ s), float64 resolution is ≈ 0.24 µs.
- Rounding to the nearest microsecond before scaling to 100 ns intervals avoids floating-point drift.
- `SetSystemTimeAsFileTime` writes UTC directly; Windows applies the user's timezone for display.

### 4. Accuracy estimate

Displayed as ±*x* ms — calculated as half the average round-trip delay of successful responses (the theoretical one-way network uncertainty).

---

## Configuration

Settings are stored at `%USERPROFILE%\.ntp_time_sync\config.json` and updated automatically when you change anything in the UI.

| Key | Default | Description |
|---|---|---|
| `servers` | 5 well-known servers | List of active NTP hostnames |
| `sync_interval` | `300` | Seconds between automatic syncs |
| `auto_sync` | `true` | Enable background sync on startup |
| `minimize_to_tray` | `true` | Close button hides to tray |
| `theme` | `"dark"` | `"dark"` or `"light"` |
| `timeout` | `3.0` | Per-server query timeout (seconds) |
| `max_log_lines` | `300` | Maximum lines kept in the sync log |

---

## Server catalog

The built-in catalog includes servers from:

| Provider | Servers |
|---|---|
| NTP Pool | Global, Europe, Asia, North America, Russia |
| Google | `time.google.com`, `time1–4.google.com`, `time.android.com` |
| Cloudflare | `time.cloudflare.com` |
| Amazon AWS | `time.aws.com`, `amazon.pool.ntp.org` |
| Microsoft | `time.windows.com` |
| Apple | `time.apple.com`, `time1–7.apple.com`, regional |
| Facebook | `time.facebook.com`, `time1–5.facebook.com` |
| NIST | 16 servers across 3 sites (NIST, WWV, Boulder) |
| USNO | `tick/tock/ntp2.usno.navy.mil` |
| HE.net | SJC, FMT, NYC |
| VNIIFTRI | Moscow, Irkutsk, Khabarovsk, Novosibirsk |
| MSK-IX | `ntp.ix.ru` |
| Stratum1/2.ru | 10 servers |
| NTP-Servers.net | 8 servers |
| Netnod | Göteborg, Malmö, Stockholm, Sundsvall |
| PTB Germany | `ptbtime1/2.ptb.de` |
| RIPE NCC | `ntp.ripe.net` |
| ISC | `clock.isc.org` |
| NICT Japan | `ntp.nict.jp` |
| NTT / MFEED | Japan |
| Chinese Academy of Sciences | `ntp.ntsc.ac.cn` |
| Hetzner | 3 servers |
| QiX / YYCIX Canada | 4 servers |
| Universities | Berkeley, GSU, Saskatchewan, MIT, UCLA and more |
| … and more | ACO.net, Trabia, TimeNL, time.in.ua, ESA, etc. |

You can add any server not in the catalog by typing its hostname in the sidebar and pressing **Enter** or **+**.

---

## File structure

```
win-time-sync-tool/
├── main.py          # Entry point; logging setup; admin warning
├── app.py           # CustomTkinter GUI, tray icon, server browser dialog
├── config.py        # Config dataclass + full NTP server catalog
├── ntp_client.py    # Concurrent NTP querying, median offset calculation
├── sync_service.py  # Background sync thread, interval countdown
├── time_setter.py   # Windows SetSystemTimeAsFileTime (100 ns precision)
└── requirements.txt
```

---

## License

MIT
