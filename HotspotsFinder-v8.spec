# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['hotspots_finder_gui_v8_final.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app.ico', '.'),
        ('logo.png', '.'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'google',
        'googleapiclient',
        'google_auth_oauthlib',
    ],
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
    name='ED Hotspots & Landables Finder v8',
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
    icon=['app.ico'],
    version='version_info_v8.txt',
)
