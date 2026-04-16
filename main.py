"""
NTP Time Sync Tool — entry point.

Usage
-----
  python main.py              # normal launch
  python main.py --admin      # re-launch elevated (Windows UAC prompt)

Administrator privileges are required to set the system clock.
Without them the tool still queries NTP servers and displays offsets,
but will not write the corrected time to the OS.
"""
from __future__ import annotations

import logging
import sys


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> None:
    _setup_logging()

    # Optional: on Windows, warn (but do not force) if not admin
    if sys.platform == "win32":
        from time_setter import is_admin
        if not is_admin():
            logging.warning(
                "Not running as administrator — "
                "NTP time correction will be disabled. "
                "Re-run as admin to enable system clock updates."
            )

    from config import Config
    from sync_service import SyncService
    from app import TimeSyncApp

    config  = Config.load()
    service = SyncService(config)
    app     = TimeSyncApp(config, service)
    app.run()


if __name__ == "__main__":
    main()
