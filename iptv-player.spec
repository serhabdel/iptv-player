# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs
import PySide6

pyside6_datas = collect_data_files('PySide6')
pyside6_binaries = collect_dynamic_libs('PySide6')
qtawesome_datas = collect_data_files('qtawesome')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=pyside6_binaries,
    datas=[('assets', 'assets'), ('src', 'src'), ('LICENSE', '.')] + pyside6_datas + qtawesome_datas,
    hiddenimports=['PySide6', 'qasync', 'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets', 'qtawesome'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['flet', 'flet_desktop', 'flet_video'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='iptv-player',
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
    icon='assets/logo.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='iptv-player',
)
