# -*- mode: python ; coding: utf-8 -*-
"""织识 PyInstaller 打包配置（onedir 模式）

用法：cd backend && pyinstaller weave.spec
产物：backend/dist/织识/织识.exe（双击启动，浏览器访问）
"""

APP_NAME = "织识"

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[
        # 前端构建产物 → 运行时位于 _MEIPASS/frontend/dist（main.py 的查找路径之一）
        ('../frontend/dist', 'frontend/dist'),
    ],
    hiddenimports=[
        # C 扩展/异步库（PyInstaller 静态分析易漏）
        'fitz',
        'anthropic',
        'aiosqlite',
        'aiofiles',
        'bs4',
        'requests',
        'dotenv',
        'docx',
        'multipart',
        # uvicorn 动态加载的协议/循环实现
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.loops.asyncio',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.protocols.websockets.websockets_impl',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # 无控制台窗口（桌面应用）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)
