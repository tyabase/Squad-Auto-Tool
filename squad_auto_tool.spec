# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['squad_auto_tool.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app_icon.ico', '.')
    ],
    hiddenimports=[
        'pkg_resources.py31_warn',
        'win32timezone',
        'pystray._win32',
        'pyautogui._pyautogui_win'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SquadAutoTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='app_icon.ico',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)