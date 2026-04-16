"""Modern CustomTkinter GUI for NTP Time Sync Tool."""
from __future__ import annotations

import datetime
import threading
import tkinter as tk
from typing import Callable, List, Optional

import customtkinter as ctk

from config import Config, SERVER_CATALOG
from ntp_client import NTPResult
from sync_service import SyncService
from time_setter import is_admin

# ── Palette ───────────────────────────────────────────────────────────────────
DOT_COLOR = {
    "ok":      "#22c55e",
    "slow":    "#f59e0b",
    "error":   "#ef4444",
    "pending": "#64748b",
}

INTERVAL_MAP: dict[str, int] = {
    "30 seconds":  30,
    "1 minute":    60,
    "5 minutes":   300,
    "15 minutes":  900,
    "30 minutes":  1800,
    "1 hour":      3600,
}


def _fmt_countdown(secs: int) -> str:
    secs = max(0, secs)
    h, r = divmod(secs, 3600)
    m, s = divmod(r, 60)
    if h:
        return f"{h}h {m:02d}m {s:02d}s"
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


# ── Server row widget ─────────────────────────────────────────────────────────

class ServerRow(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkScrollableFrame, server: str,
                 on_remove: Callable[[str], None], **kw):
        super().__init__(parent, corner_radius=8, **kw)
        self.server = server
        self.grid_columnconfigure(1, weight=1)

        self._dot = ctk.CTkLabel(self, text="●", width=18,
                                 font=("Segoe UI", 13),
                                 text_color=DOT_COLOR["pending"])
        self._dot.grid(row=0, column=0, padx=(8, 2), pady=(6, 1))

        self._name = ctk.CTkLabel(self, text=server, anchor="w",
                                  font=("Segoe UI", 11, "bold"))
        self._name.grid(row=0, column=1, sticky="ew", padx=(4, 2), pady=(6, 1))

        ctk.CTkButton(
            self, text="✕", width=22, height=22,
            fg_color="transparent",
            hover_color=("#fee2e2", "#7f1d1d"),
            text_color=("#ef4444", "#f87171"),
            command=lambda: on_remove(server),
        ).grid(row=0, column=2, padx=(2, 8), pady=(6, 1))

        self._stats = ctk.CTkLabel(
            self, text="awaiting first sync…", anchor="w",
            font=("Consolas", 10),
            text_color=("#64748b", "#94a3b8"),
        )
        self._stats.grid(row=1, column=0, columnspan=3,
                         sticky="ew", padx=(28, 8), pady=(0, 6))

    def set_pending(self) -> None:
        self._dot.configure(text_color=DOT_COLOR["pending"])
        self._stats.configure(text="querying…")

    def update_result(self, r: NTPResult) -> None:
        if not r.success:
            self._dot.configure(text_color=DOT_COLOR["error"])
            self._stats.configure(text=f"✗  {r.error or 'failed'}")
            return
        color = "slow" if abs(r.offset_ms) > 200 or r.delay_ms > 300 else "ok"
        self._dot.configure(text_color=DOT_COLOR[color])
        self._stats.configure(
            text=(f"offset {r.offset_us:+.2f} µs   "
                  f"rtt {r.delay_ms:.2f} ms   "
                  f"S{r.stratum}")
        )


# ── Server catalog dialog ─────────────────────────────────────────────────────

class ServerBrowserDialog(ctk.CTkToplevel):
    def __init__(self, parent, config: Config,
                 on_apply: Callable[[list[str]], None]):
        super().__init__(parent)
        self.title("Server Catalog")
        self.geometry("700x500")
        self.resizable(True, True)
        self.grab_set()

        self._config = config
        self._on_apply = on_apply
        self._vars: dict[str, tk.BooleanVar] = {}
        self._active_cat: Optional[str] = None
        self._cat_btns: dict[str, ctk.CTkButton] = {}

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Left — category list
        left = ctk.CTkFrame(self, width=190, corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 1), pady=0)
        left.grid_propagate(False)
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left, text="Provider",
                     font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 6))

        scroll_cats = ctk.CTkScrollableFrame(left, fg_color="transparent",
                                             corner_radius=0)
        scroll_cats.grid(row=1, column=0, sticky="nsew")
        scroll_cats.grid_columnconfigure(0, weight=1)

        for cat in SERVER_CATALOG:
            btn = ctk.CTkButton(
                scroll_cats, text=cat, anchor="w", height=28,
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("#dbeafe", "#1e3a5f"),
                command=lambda c=cat: self._show_cat(c),
            )
            btn.grid(sticky="ew", padx=4, pady=1)
            self._cat_btns[cat] = btn

        # Right — server checkboxes
        self._right_scroll = ctk.CTkScrollableFrame(self, corner_radius=0)
        self._right_scroll.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self._right_scroll.grid_columnconfigure(0, weight=1)

        # Footer
        footer = ctk.CTkFrame(self, fg_color="transparent", height=44)
        footer.grid(row=1, column=0, columnspan=2, sticky="ew",
                    padx=12, pady=(4, 8))
        footer.grid_columnconfigure(0, weight=1)

        self._status = ctk.CTkLabel(footer, text="",
                                    font=("Segoe UI", 10),
                                    text_color=("#64748b", "#94a3b8"))
        self._status.grid(row=0, column=0, sticky="w")

        ctk.CTkButton(footer, text="Cancel", width=80,
                      fg_color="transparent",
                      command=self.destroy).grid(row=0, column=2, padx=(4, 0))
        ctk.CTkButton(footer, text="Apply", width=80,
                      command=self._apply).grid(row=0, column=1, padx=(4, 4))

        # Show first category
        if SERVER_CATALOG:
            self._show_cat(next(iter(SERVER_CATALOG)))

    def _show_cat(self, cat: str) -> None:
        if self._active_cat:
            self._cat_btns[self._active_cat].configure(fg_color="transparent")
        self._active_cat = cat
        self._cat_btns[cat].configure(fg_color=("#bfdbfe", "#1e3a5f"))

        for w in self._right_scroll.winfo_children():
            w.destroy()

        servers = SERVER_CATALOG[cat]
        ctk.CTkLabel(
            self._right_scroll,
            text=f"{cat}   ({len(servers)} servers)",
            font=("Segoe UI", 11, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(8, 6))

        for i, srv in enumerate(servers, 1):
            if srv not in self._vars:
                self._vars[srv] = tk.BooleanVar(
                    value=(srv in self._config.servers))
            ctk.CTkCheckBox(
                self._right_scroll, text=srv,
                font=("Consolas", 11),
                variable=self._vars[srv],
                command=self._refresh_status,
            ).grid(row=i, column=0, sticky="w", padx=16, pady=2)

        self._refresh_status()

    def _refresh_status(self) -> None:
        n = sum(1 for v in self._vars.values() if v.get())
        self._status.configure(text=f"{n} server(s) selected")

    def _apply(self) -> None:
        selected = [s for s, v in self._vars.items() if v.get()]
        self._on_apply(selected)
        self.destroy()


# ── Log panel ─────────────────────────────────────────────────────────────────

class LogPanel(ctk.CTkFrame):
    def __init__(self, parent, max_lines: int = 300, **kw):
        super().__init__(parent, corner_radius=0, **kw)
        self._max = max_lines
        self._count = 0

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=10, pady=(6, 2))
        hdr.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text="Sync Log",
                     font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, sticky="w")
        ctk.CTkButton(hdr, text="Clear", width=55, height=22,
                      command=self._clear).grid(row=0, column=1)

        self._box = ctk.CTkTextbox(
            self, state="disabled", height=130,
            font=("Consolas", 10), wrap="word",
        )
        self._box.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

    def append(self, msg: str) -> None:
        ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self._box.configure(state="normal")
        if self._count >= self._max:
            self._box.delete("1.0", "2.0")
        self._box.insert("end", f"[{ts}]  {msg}\n")
        self._box.see("end")
        self._box.configure(state="disabled")
        self._count += 1

    def _clear(self) -> None:
        self._box.configure(state="normal")
        self._box.delete("1.0", "end")
        self._box.configure(state="disabled")
        self._count = 0


# ── Main application window ───────────────────────────────────────────────────

class TimeSyncApp:
    WIN_W, WIN_H = 1020, 700
    SIDEBAR_W    = 310

    def __init__(self, config: Config, service: SyncService) -> None:
        self.config  = config
        self.service = service
        self._rows: dict[str, ServerRow] = {}
        self._tray   = None

        ctk.set_appearance_mode(config.theme)
        ctk.set_default_color_theme("blue")

        self._root = ctk.CTk()
        self._root.title("NTP Time Sync")
        self._root.geometry(f"{self.WIN_W}x{self.WIN_H}")
        self._root.minsize(780, 540)
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self._wire_service()
        self._tick_clock()
        self._init_tray()

    # ── Public entry point ────────────────────────────────────────────────────
    def run(self) -> None:
        if self.config.auto_sync:
            self.service.start()
        self._root.mainloop()

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        self._root.grid_rowconfigure(1, weight=1)
        self._root.grid_columnconfigure(0, weight=1)
        self._build_header()
        self._build_body()
        self._build_log()

    # ·· Header bar ···········································
    def _build_header(self) -> None:
        bar = ctk.CTkFrame(self._root, corner_radius=0, height=54)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(bar, text="⏱  NTP Time Sync",
                     font=("Segoe UI", 15, "bold")).grid(
            row=0, column=0, padx=18, sticky="w")

        # Admin badge
        admin = is_admin()
        badge_text  = "  🔑 Running as Administrator" if admin \
                      else "  ⚠  No admin — time sync disabled"
        badge_color = ("#16a34a", "#4ade80") if admin else ("#b45309", "#fbbf24")
        ctk.CTkLabel(bar, text=badge_text, font=("Segoe UI", 11),
                     text_color=badge_color).grid(
            row=0, column=1, padx=8, sticky="w")

        ctk.CTkButton(bar, text="☀ / 🌙", width=80, height=32,
                      command=self._toggle_theme).grid(
            row=0, column=2, padx=4)
        ctk.CTkButton(bar, text="⬛ Tray", width=80, height=32,
                      command=self._hide_to_tray).grid(
            row=0, column=3, padx=(4, 18))

    # ·· Body (sidebar + dashboard) ···························
    def _build_body(self) -> None:
        body = ctk.CTkFrame(self._root, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        self._build_sidebar(body)
        self._build_dashboard(body)

    # ·· Sidebar — server list ·······················
    def _build_sidebar(self, parent) -> None:
        side = ctk.CTkFrame(parent, width=self.SIDEBAR_W, corner_radius=0)
        side.grid(row=0, column=0, sticky="nsew")
        side.grid_propagate(False)
        side.grid_rowconfigure(1, weight=1)
        side.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(side, text="Active Servers",
                     font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, padx=14, pady=(12, 4), sticky="w")

        self._scroll = ctk.CTkScrollableFrame(
            side, fg_color="transparent", corner_radius=0)
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=4)
        self._scroll.grid_columnconfigure(0, weight=1)

        # Add-server controls
        add_bar = ctk.CTkFrame(side, fg_color="transparent")
        add_bar.grid(row=2, column=0, sticky="ew", padx=8, pady=6)
        add_bar.grid_columnconfigure(0, weight=1)

        self._add_entry = ctk.CTkEntry(add_bar,
                                       placeholder_text="hostname or IP…",
                                       height=32)
        self._add_entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self._add_entry.bind("<Return>", lambda _e: self._add_server())

        ctk.CTkButton(add_bar, text="+", width=32, height=32,
                      command=self._add_server).grid(row=0, column=1)

        ctk.CTkButton(add_bar, text="Browse Catalog…", height=32,
                      command=self._open_catalog).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))

        self._rebuild_rows()

    # ·· Dashboard — clock + controls ·················
    def _build_dashboard(self, parent) -> None:
        dash = ctk.CTkFrame(parent, fg_color="transparent")
        dash.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        dash.grid_rowconfigure(0, weight=1)
        dash.grid_columnconfigure(0, weight=1)

        # ── Time card ────────────────────────────────
        time_card = ctk.CTkFrame(dash, corner_radius=14)
        time_card.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        time_card.grid_columnconfigure(0, weight=1)

        self._lbl_clock = ctk.CTkLabel(
            time_card,
            text="--:--:--.------",
            font=("Segoe UI Mono", 54, "bold"),
            text_color=("#1d4ed8", "#60a5fa"),
        )
        self._lbl_clock.grid(row=0, column=0, pady=(22, 2))

        self._lbl_date = ctk.CTkLabel(
            time_card, text="", font=("Segoe UI", 15))
        self._lbl_date.grid(row=1, column=0, pady=(0, 2))

        self._lbl_tz = ctk.CTkLabel(
            time_card, text="",
            font=("Segoe UI", 11),
            text_color=("#64748b", "#94a3b8"))
        self._lbl_tz.grid(row=2, column=0, pady=(0, 16))

        # Stats strip
        stats = ctk.CTkFrame(time_card, fg_color=("gray90", "gray20"),
                             corner_radius=8)
        stats.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 20))
        for col in range(3):
            stats.grid_columnconfigure(col, weight=1)

        self._lbl_offset   = self._stat_label(stats, "Offset: —",    0)
        self._lbl_accuracy = self._stat_label(stats, "Accuracy: —",  1)
        self._lbl_srv_ok   = self._stat_label(stats, "Servers: —",   2)

        # ── Controls card ────────────────────────────
        ctrl = ctk.CTkFrame(dash, corner_radius=14)
        ctrl.grid(row=1, column=0, sticky="ew")
        ctrl.grid_columnconfigure(1, weight=1)

        self._btn_sync = ctk.CTkButton(
            ctrl, text="🔄  Sync Now", height=46,
            font=("Segoe UI", 14, "bold"),
            command=self._manual_sync,
        )
        self._btn_sync.grid(row=0, column=0, columnspan=2,
                            sticky="ew", padx=16, pady=(16, 10))

        def _row(r: int, label: str) -> None:
            ctk.CTkLabel(ctrl, text=label,
                         font=("Segoe UI", 12)).grid(
                row=r, column=0, padx=(16, 8), pady=4, sticky="w")

        _row(1, "Auto-sync:")
        self._sw_auto = ctk.CTkSwitch(ctrl, text="",
                                      command=self._toggle_auto)
        if self.config.auto_sync:
            self._sw_auto.select()
        self._sw_auto.grid(row=1, column=1, sticky="w", pady=4)

        _row(2, "Interval:")
        cur = next((k for k, v in INTERVAL_MAP.items()
                    if v == self.config.sync_interval), "5 minutes")
        self._opt_interval = ctk.CTkOptionMenu(
            ctrl, values=list(INTERVAL_MAP.keys()),
            width=160, command=self._set_interval)
        self._opt_interval.set(cur)
        self._opt_interval.grid(row=2, column=1, sticky="w", pady=4)

        self._lbl_next = ctk.CTkLabel(
            ctrl, text="Next sync: —",
            font=("Segoe UI", 11),
            text_color=("#64748b", "#94a3b8"))
        self._lbl_next.grid(row=3, column=0, columnspan=2,
                            padx=16, pady=(2, 4), sticky="w")

        self._lbl_last = ctk.CTkLabel(
            ctrl, text="Last sync: never",
            font=("Segoe UI", 11),
            text_color=("#64748b", "#94a3b8"))
        self._lbl_last.grid(row=4, column=0, columnspan=2,
                            padx=16, pady=(0, 16), sticky="w")

    @staticmethod
    def _stat_label(parent, text: str, col: int) -> ctk.CTkLabel:
        lbl = ctk.CTkLabel(parent, text=text, font=("Consolas", 11))
        lbl.grid(row=0, column=col, padx=14, pady=8)
        return lbl

    # ·· Log panel ····································
    def _build_log(self) -> None:
        self._log = LogPanel(self._root,
                             max_lines=self.config.max_log_lines)
        self._log.grid(row=2, column=0, sticky="ew")

    # ── Server list management ────────────────────────────────────────────────
    def _rebuild_rows(self) -> None:
        for w in self._scroll.winfo_children():
            w.destroy()
        self._rows.clear()
        for i, srv in enumerate(self.config.servers):
            row = ServerRow(self._scroll, srv,
                            on_remove=self._remove_server)
            row.grid(row=i, column=0, sticky="ew", padx=4, pady=2)
            self._rows[srv] = row

    def _add_server(self) -> None:
        val = self._add_entry.get().strip().lower()
        if val and val not in self.config.servers:
            self.config.servers.append(val)
            self.config.save()
            self._add_entry.delete(0, "end")
            self._rebuild_rows()

    def _remove_server(self, srv: str) -> None:
        if srv in self.config.servers:
            self.config.servers.remove(srv)
            self.config.save()
            self._rebuild_rows()

    def _open_catalog(self) -> None:
        def on_apply(selected: list[str]) -> None:
            changed = False
            for s in selected:
                if s not in self.config.servers:
                    self.config.servers.append(s)
                    changed = True
            # Remove servers that were unchecked in the dialog
            to_remove = [s for s in list(self.config.servers)
                         if s in {srv for cat in SERVER_CATALOG.values()
                                  for srv in cat}
                         and s not in selected]
            for s in to_remove:
                self.config.servers.remove(s)
                changed = True
            if changed:
                self.config.save()
                self._rebuild_rows()

        ServerBrowserDialog(self._root, self.config, on_apply)

    # ── Service wiring ────────────────────────────────────────────────────────
    def _wire_service(self) -> None:
        def post(fn: Callable) -> Callable:
            """Wrap a callback so it is always executed on the Tk main thread."""
            def wrapper(*args):
                self._root.after(0, lambda: fn(*args))
            return wrapper

        self.service.on_sync_start = post(self._on_sync_start)
        self.service.on_sync_done  = post(self._on_sync_done)
        self.service.on_tick       = post(self._on_tick)

    def _on_sync_start(self) -> None:
        self._btn_sync.configure(text="⌛  Syncing…", state="disabled")
        for row in self._rows.values():
            row.set_pending()
        self._log.append("Querying NTP servers…")

    def _on_sync_done(self, results: List[NTPResult],
                      offset: Optional[float],
                      success: bool, msg: str) -> None:
        self._btn_sync.configure(text="🔄  Sync Now", state="normal")

        for r in results:
            if r.server in self._rows:
                self._rows[r.server].update_result(r)

        ok  = sum(1 for r in results if r.success)
        tot = len(results)
        self._lbl_srv_ok.configure(text=f"Servers: {ok}/{tot}")

        if offset is not None:
            us = offset * 1_000_000
            self._lbl_offset.configure(
                text=f"Offset: {us:+.2f} µs")
            good = [r for r in results if r.success]
            if good:
                acc_ms = sum(r.delay for r in good) / len(good) / 2 * 1000
                self._lbl_accuracy.configure(
                    text=f"Accuracy: ±{acc_ms:.3f} ms")

        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self._lbl_last.configure(text=f"Last sync: {ts}")
        icon = "✓" if success else "✗"
        self._log.append(f"{icon}  {msg}")

    def _on_tick(self, remaining: int) -> None:
        self._lbl_next.configure(
            text=f"Next sync: {_fmt_countdown(remaining)}")

    # ── Live clock (30 fps) ───────────────────────────────────────────────────
    def _tick_clock(self) -> None:
        now = datetime.datetime.now().astimezone()
        self._lbl_clock.configure(text=now.strftime("%H:%M:%S.%f"))
        self._lbl_date.configure(text=now.strftime("%A, %B %d, %Y"))
        tz_off  = now.strftime("%z")   # e.g. "+0300"
        tz_name = now.strftime("%Z")   # e.g. "MSK"
        if tz_off:
            tz_str = f"UTC{tz_off[:3]}:{tz_off[3:]}  ({tz_name})"
        else:
            tz_str = tz_name
        self._lbl_tz.configure(text=tz_str)
        self._root.after(33, self._tick_clock)   # ≈30 fps

    # ── Control handlers ──────────────────────────────────────────────────────
    def _manual_sync(self) -> None:
        self.service.trigger()

    def _toggle_auto(self) -> None:
        self.config.auto_sync = bool(self._sw_auto.get())
        self.config.save()
        if self.config.auto_sync:
            self.service.start()
        else:
            self.service.stop()

    def _set_interval(self, label: str) -> None:
        self.config.sync_interval = INTERVAL_MAP.get(label, 300)
        self.config.save()

    def _toggle_theme(self) -> None:
        new = "light" if ctk.get_appearance_mode() == "Dark" else "dark"
        ctk.set_appearance_mode(new)
        self.config.theme = new
        self.config.save()

    # ── System tray ───────────────────────────────────────────────────────────
    def _init_tray(self) -> None:
        try:
            import pystray
            from PIL import Image, ImageDraw

            sz = 64
            img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
            d   = ImageDraw.Draw(img)
            cx = cy = sz // 2
            r  = sz // 2 - 3
            # Filled circle background
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#1d4ed8")
            # Clock rim
            d.ellipse([cx - r + 2, cy - r + 2, cx + r - 2, cy + r - 2],
                      outline="white", width=2)
            # Hour hand (12 o'clock)
            d.line([cx, cy, cx, cy - r + 8], fill="white", width=3)
            # Minute hand (3 o'clock)
            d.line([cx, cy, cx + r - 8, cy], fill="white", width=2)
            # Centre dot
            d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill="white")

            menu = pystray.Menu(
                pystray.MenuItem(
                    "Open", lambda _i, _it: self._root.after(0, self._show_window)),
                pystray.MenuItem(
                    "Sync Now", lambda _i, _it: self._root.after(0, self._manual_sync)),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "Exit", lambda _i, _it: self._root.after(0, self._quit)),
            )
            self._tray = pystray.Icon(
                "NTPSync", img, "NTP Time Sync", menu)
            threading.Thread(target=self._tray.run,
                             daemon=True, name="TrayIcon").start()
        except Exception:
            self._tray = None   # pystray / Pillow not available

    def _hide_to_tray(self) -> None:
        self._root.withdraw()

    def _show_window(self) -> None:
        self._root.deiconify()
        self._root.lift()
        self._root.focus_force()

    def _on_close(self) -> None:
        if self.config.minimize_to_tray and self._tray:
            self._hide_to_tray()
        else:
            self._quit()

    def _quit(self) -> None:
        self.service.stop()
        if self._tray:
            try:
                self._tray.stop()
            except Exception:
                pass
        self.config.save()
        self._root.quit()
        self._root.destroy()
