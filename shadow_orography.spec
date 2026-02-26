# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Shadow Orography Studio on Windows.

Build with (same interpreter/venv that has project deps installed):
    python -m PyInstaller --clean --noconfirm shadow_orography.spec
"""

from PyInstaller.utils.hooks import collect_all

# collect_all is more robust than only collect_submodules: it includes
# hidden imports + package data + binaries needed by pandas at runtime.
pandas_datas, pandas_binaries, pandas_hiddenimports = collect_all("pandas")


a = Analysis(
    ["src/shadow_orography/main.py"],
    pathex=["src"],
    binaries=pandas_binaries,
    datas=pandas_datas,
    hiddenimports=pandas_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ShadowOrography",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
