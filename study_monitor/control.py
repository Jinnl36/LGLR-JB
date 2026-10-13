"""本机遥控：让 Siri / 快捷指令 / 命令行控制正在运行的学习监督器。

运行中的程序在 127.0.0.1 上监听一个端口；
`python -m study_monitor start|stop|status` 连上去发命令，并把回复打印出来（快捷指令可以让 Siri 念出来）。"""

import os
import queue
import socket
import threading
import time
from typing import Callable, Optional

HOST = "127.0.0.1"
PORT = 47321
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 程序没开时，“开始”命令会先写这个文件再启动程序，程序启动后看到它就自动开始学习模式
AUTOSTART_FLAG = os.path.join(PROJECT_DIR, ".autostart")


def send_command(cmd: str, timeout: float = 15) -> Optional[str]:
    """发送命令并返回回复；程序没在运行时返回 None。"""
    try:
        with socket.create_connection((HOST, PORT), timeout=2) as s:
            s.settimeout(timeout)
            s.sendall((cmd + "\n").encode("utf-8"))
            with s.makefile(encoding="utf-8") as f:
                return f.read().strip()
    except OSError:
        return None


def consume_autostart_flag(max_age_sec: float = 300) -> bool:
    """有新鲜的自动开始标记就删掉并返回 True（太旧的标记直接丢弃）。"""
    try:
        fresh = time.time() - os.path.getmtime(AUTOSTART_FLAG) < max_age_sec
        os.remove(AUTOSTART_FLAG)
        return fresh
    except OSError:
        return False


class ControlServer:
    """在后台线程接收命令，交给界面线程处理（tkinter 只能在主线程操作）。"""

    def __init__(self):
        self.requests: "queue.Queue[tuple]" = queue.Queue()
        self.ok = False
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.bind((HOST, PORT))
            self._sock.listen(4)
            self.ok = True
            threading.Thread(target=self._serve, daemon=True).start()
        except OSError:  # 端口被占用：大概已经开着一个了
            pass

    def _serve(self) -> None:
        while True:
            conn, _ = self._sock.accept()
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn: socket.socket) -> None:
        with conn:
            try:
                conn.settimeout(5)
                with conn.makefile(encoding="utf-8") as f:
                    cmd = f.readline().strip().lower()
                done = threading.Event()
                box = {"reply": "学习监督器没有响应，请看一下电脑上的窗口。"}
                self.requests.put((cmd, box, done))
                done.wait(10)
                conn.sendall(box["reply"].encode("utf-8"))
            except OSError:
                pass

    def process_pending(self, handler: Callable[[str], str]) -> None:
        """在界面线程里调用：处理排队的命令。"""
        while True:
            try:
                cmd, box, done = self.requests.get_nowait()
            except queue.Empty:
                return
            try:
                box["reply"] = handler(cmd)
            finally:
                done.set()
