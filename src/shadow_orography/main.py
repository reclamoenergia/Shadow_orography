"""Application entrypoint."""

from __future__ import annotations

import os
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path

__all__ = ["run"]


def _startup_log_path() -> Path:
    """Return the startup log location, overridable for tests/debugging."""
    custom_path = os.getenv("SHADOW_OROGRAPHY_STARTUP_LOG")
    if custom_path:
        return Path(custom_path)
    return Path(tempfile.gettempdir()) / "shadow_orography_startup.log"


def _append_startup_log(message: str) -> None:
    """Append a timestamped line to the startup log."""
    log_path = _startup_log_path()
    timestamp = datetime.now().astimezone().isoformat()
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message}\n")


def _log_exception(exc: BaseException, context: str) -> None:
    """Persist a startup exception and print a readable hint for console users."""
    _append_startup_log(f"{context}: {exc!r}")
    with _startup_log_path().open("a", encoding="utf-8") as handle:
        traceback.print_exception(type(exc), exc, exc.__traceback__, file=handle)

    print(
        "Errore di avvio Shadow Orography. "
        f"Consulta il log: {_startup_log_path()}",
        file=sys.stderr,
    )


def _load_gui_run_callable():
    """Import GUI lazily to ensure startup exceptions are always logged."""
    from shadow_orography.gui.app import run as gui_run

    return gui_run


def run() -> None:
    """Start the desktop application with robust startup diagnostics."""
    _append_startup_log("App startup")
    try:
        gui_run = _load_gui_run_callable()
        gui_run()
    except BaseException as exc:
        _log_exception(exc, "Fatal startup error")
        raise


if __name__ == "__main__":
    run()
