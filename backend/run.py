"""织识桌面版启动器 —— 单实例锁 + 端口探测 + 自动开浏览器 + uvicorn 启动

打包入口（PyInstaller weave.spec 的 scripts=[run.py]）。
开发模式仍用 `uvicorn main:app`，本文件仅打包版使用。
"""

import msvcrt
import os
import socket
import threading
import webbrowser

APP_NAME = "织识"
BROWSER_OPEN_DELAY = 1.5  # 服务就绪后延迟打开浏览器


def _default_data_dir() -> str:
    """%APPDATA%\\织识（无 APPDATA 时退回用户主目录）"""
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
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
    """锁文件 + Windows 排他锁（msvcrt.LK_NBLCK）。

    成功返回 True（进程存活期间持有）；已有实例返回 False。
    进程退出时 fd 自动释放，锁文件残留无影响（每次重新打开加锁）。
    """
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR)
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        return True
    except OSError:
        return False


def open_browser_later(port: int):
    def _open():
        import time
        time.sleep(BROWSER_OPEN_DELAY)
        webbrowser.open(f"http://localhost:{port}")

    threading.Thread(target=_open, daemon=True).start()


def main():
    # 数据目录：环境变量未设置时默认 %APPDATA%\织识
    data_dir = os.environ.get("WEAVE_DATA_DIR") or _default_data_dir()
    os.environ["WEAVE_DATA_DIR"] = data_dir

    # 单实例锁：已运行则提示并打开既有实例
    if not acquire_single_instance(os.path.join(data_dir, "weave.lock")):
        print(f"{APP_NAME}已在运行，打开既有实例…")
        webbrowser.open(f"http://localhost:8000")
        return

    try:
        port = find_free_port(8000)
        print(f"{APP_NAME}启动中 → http://localhost:{port}")
        print(f"数据目录：{data_dir}")
        open_browser_later(port)

        import uvicorn
        from main import app
        uvicorn.run(app, host="127.0.0.1", port=port)
    finally:
        pass  # 锁随进程退出自动释放（fd 由 OS 回收）


if __name__ == "__main__":
    main()
