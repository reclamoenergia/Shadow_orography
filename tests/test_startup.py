from __future__ import annotations

from pathlib import Path

import pytest

from shadow_orography import main


def test_run_logs_startup_and_calls_gui(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    log_path = tmp_path / "startup.log"
    monkeypatch.setenv("SHADOW_OROGRAPHY_STARTUP_LOG", str(log_path))

    called = {"value": False}

    def fake_gui_run() -> None:
        called["value"] = True

    monkeypatch.setattr(main, "_load_gui_run_callable", lambda: fake_gui_run)

    main.run()

    assert called["value"] is True
    content = log_path.read_text(encoding="utf-8")
    assert "App startup" in content


def test_run_logs_and_reraises_startup_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "startup.log"
    monkeypatch.setenv("SHADOW_OROGRAPHY_STARTUP_LOG", str(log_path))

    def fake_gui_run() -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(main, "_load_gui_run_callable", lambda: fake_gui_run)

    with pytest.raises(RuntimeError, match="boom"):
        main.run()

    content = log_path.read_text(encoding="utf-8")
    assert "Fatal startup error" in content
    assert "RuntimeError: boom" in content


def test_run_reports_missing_pandas_with_friendly_message(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "startup.log"
    monkeypatch.setenv("SHADOW_OROGRAPHY_STARTUP_LOG", str(log_path))
    monkeypatch.setattr(main.sys, "frozen", True, raising=False)

    def fake_loader():
        raise ModuleNotFoundError("No module named 'pandas'", name="pandas")

    monkeypatch.setattr(main, "_load_gui_run_callable", fake_loader)

    with pytest.raises(RuntimeError, match="Dipendenza mancante"):
        main.run()

    content = log_path.read_text(encoding="utf-8")
    assert "pandas" in content
    assert "shadow_orography.spec" in content
    assert "collect-submodules pandas" in content


def test_run_reports_missing_pandas_in_dev_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "startup.log"
    monkeypatch.setenv("SHADOW_OROGRAPHY_STARTUP_LOG", str(log_path))
    monkeypatch.delattr(main.sys, "frozen", raising=False)

    def fake_loader():
        raise ModuleNotFoundError("No module named 'pandas.core'", name="pandas.core")

    monkeypatch.setattr(main, "_load_gui_run_callable", fake_loader)

    with pytest.raises(RuntimeError, match="Installa le dipendenze del progetto"):
        main.run()

    content = log_path.read_text(encoding="utf-8")
    assert "Dipendenza Python mancante" in content
