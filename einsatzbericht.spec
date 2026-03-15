# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec für Einsatzbericht Manager
Schlanke Version – nur tatsächlich benötigte Qt-Module.
"""

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

a = Analysis(
    ['main.py'],
    pathex=[r'E:\mines schummel'],
    binaries=[],
    datas=[
        # Konfigurationsvorlage
        (r'config.ini.example', '.'),
        # Beispiel-PDFs
        (r'examples', 'examples'),
        # certifi CA-Zertifikate (benötigt von httpx/anthropic)
        *collect_data_files('certifi'),
        # reportlab Schriften/Ressourcen
        *collect_data_files('reportlab'),
        # python-docx Templates
        *collect_data_files('docx'),
    ],
    hiddenimports=[
        # PySide6 – nur die genutzten Module
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtPrintSupport',
        # anthropic + Netzwerk
        'anthropic',
        'anthropic._models',
        'anthropic.types',
        'anthropic.resources',
        'anthropic.resources.messages',
        'anthropic.resources.models',
        'httpx',
        'httpcore',
        'httpcore._sync.connection',
        'httpcore._sync.http11',
        'httpcore._sync.connection_pool',
        'httpcore._async.connection',
        'httpcore._async.http11',
        'httpcore._async.connection_pool',
        'certifi',
        'anyio',
        'anyio._backends._asyncio',
        'anyio._backends._trio',
        'sniffio',
        'h11',
        # reportlab
        *collect_submodules('reportlab'),
        # python-docx
        *collect_submodules('docx'),
        # odfpy
        *collect_submodules('odf'),
        # pypdf
        'pypdf',
        'pypdf._reader',
        'pypdf.generic',
        # stdlib
        'sqlite3',
        '_sqlite3',
        'configparser',
        'zipfile',
        'xml.etree.ElementTree',
        'email',
        'email.mime.multipart',
        'email.mime.base',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'tkinter', 'unittest', 'test', 'pytest',
        'PySide6.Qt3DAnimation', 'PySide6.Qt3DCore', 'PySide6.Qt3DExtras',
        'PySide6.Qt3DInput', 'PySide6.Qt3DLogic', 'PySide6.Qt3DRender',
        'PySide6.QtBluetooth', 'PySide6.QtCharts', 'PySide6.QtDataVisualization',
        'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets',
        'PySide6.QtNfc', 'PySide6.QtPositioning', 'PySide6.QtLocation',
        'PySide6.QtRemoteObjects', 'PySide6.QtSensors', 'PySide6.QtSerialPort',
        'PySide6.QtSql', 'PySide6.QtTest', 'PySide6.QtWebChannel',
        'PySide6.QtWebEngine', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebSockets', 'PySide6.QtAxContainer',
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='EinsatzberichtManager',
    debug=False,
    strip=False,
    upx=False,
    console=False,       # kein schwarzes Konsolenfenster
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='EinsatzberichtManager',
)
