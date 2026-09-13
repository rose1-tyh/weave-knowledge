"""织识桌面版启动器 —— 原生窗口（pywebview）+ 单实例锁 + 端口探测

打包入口（PyInstaller weave.spec 的 scripts=[run.py]）。
开发模式仍用 `uvicorn main:app`，本文件仅打包版/一体化启动使用。

UI 模式选择（优先级从高到低）：
1. `--browser` 命令行参数 或 WEAVE_UI=browser → 系统浏览器（无窗口依赖）
2. pywebview 可用 → 原生窗口（Windows 走 WebView2，需 Win10+）
3. 兜底 → 系统浏览器

数据目录：环境变量 WEAVE_DATA_DIR 优先，默认 %APPDATA%\\织识（非 Windows 回退 ~/织识）。
"""

import argparse
import os
import socket
import threading
import webbrowser

APP_NAME = "织识"

# 服务就绪探测：最多等 20s（首启含建表/索引）
HEALTH_TIMEOUT = 20.0


def _default_data_dir() -> str:
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(base, APP_NAME)


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def find_free_port(start: int = 8000, max_tries: int = 10) -> int:
    """从 start 起探测第一个可用端口"""
    for port in range(start, start + max_tries):
        if not _port_in_use(port):
            return port
    raise RuntimeError(f"端口 {start}-{start + max_tries - 1} 均被占用，无法启动")


def acquire_single_instance(lock_path: str) -> bool:
    """锁文件 + 排他锁（Windows: msvcrt / POSIX: fcntl），进程存活期间持有。

    成功返回 True；已有实例返回 False。锁随进程退出自动释放，残留文件无影响。
    """
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR)
    except OSError:
        return True  # 锁文件不可建（权限等）→ 不阻塞启动
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except (ImportError, OSError):
        return False


def _wait_health(port: int, timeout: float = HEALTH_TIMEOUT) -> bool:
    """轮询 /api/health 直到服务就绪"""
    import time
    import urllib.request

    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{port}/api/health"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.2)
    return False


def start_server(port: int):
    """后台线程启动 uvicorn，返回 (server, thread)；健康探测通过后返回"""
    import uvicorn
    from main import app

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    if not _wait_health(port):
        raise RuntimeError("后端服务启动超时")
    return server, thread


def open_in_browser(port: int):
    print(f"{APP_NAME} → http://localhost:{port}（浏览器模式，Ctrl+C 退出）")
    webbrowser.open(f"http://localhost:{port}")
    threading.Event().wait()  # 阻塞至进程终止


def open_in_window(port: int) -> None:
    """原生窗口模式：webview 阻塞至窗口关闭，随后通知服务退出"""
    import webview

    webview.create_window(
        APP_NAME,
        f"http://127.0.0.1:{port}",
        width=1440,
        height=900,
        min_size=(960, 640),
        background_color="#080c14",
    )
    webview.start()


def main():
    parser = argparse.ArgumentParser(description=f"{APP_NAME}桌面版")
    parser.add_argument("--browser", action="store_true", help="使用系统浏览器而非原生窗口")
    args = parser.parse_args()

    # 数据目录：环境变量未设置时按平台默认
    data_dir = os.environ.get("WEAVE_DATA_DIR") or _default_data_dir()
    os.environ["WEAVE_DATA_DIR"] = data_dir

    # 单实例：已运行 → 直接唤起既有实例（窗口模式下此前端口的窗口仍在前台）
    if not acquire_single_instance(os.path.join(data_dir, "weave.lock")):
        print(f"{APP_NAME}已在运行，打开既有实例…")
        webbrowser.open("http://localhost:8000")
        return

    # 应用模式标记：前端据此启用「记住上次页面」等桌面行为
    os.environ["WEAVE_APP_MODE"] = "1"

    try:
        port = find_free_port(8000)
    except RuntimeError as e:
        print(e)
        return

    print(f"{APP_NAME}启动中 → http://localhost:{port}")
    print(f"数据目录：{data_dir}")

    try:
        server, _thread = start_server(port)
    except Exception as e:
        print(f"服务启动失败：{e}")
        return

    use_window = not args.browser and os.environ.get("WEAVE_UI", "").lower() != "browser"
    if use_window:
        try:
            open_in_window(port)
            return
        except Exception as e:
            # WebView2 缺失/初始化失败 → 浏览器兜底（服务已在运行，无需重启）
            print(f"原生窗口不可用（{e}），回退浏览器模式…")
    try:
        open_in_browser(port)
    finally:
        server.should_exit = True


if __name__ == "__main__":
    main()
