"""跨平台获取：当前前台窗口标题 / 进程名、键鼠空闲时间。"""

import platform
import subprocess
from dataclasses import dataclass
from typing import Optional

try:
    import psutil
except ImportError:  # psutil 是可选的，只影响进程名
    psutil = None

SYSTEM = platform.system()


@dataclass
class WindowInfo:
    title: str = ""
    process: str = ""

    def text(self) -> str:
        return f"{self.process} {self.title}".strip()


def _process_name(pid: int) -> str:
    if psutil is None or not pid:
        return ""
    try:
        return psutil.Process(pid).name()
    except Exception:
        return ""


def _active_window_windows() -> WindowInfo:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return WindowInfo()
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return WindowInfo(title=buf.value, process=_process_name(pid.value))


def _active_window_macos() -> WindowInfo:
    script = (
        'tell application "System Events"\n'
        '  set p to first application process whose frontmost is true\n'
        '  set n to name of p\n'
        '  set t to ""\n'
        '  try\n'
        '    set t to name of front window of p\n'
        '  end try\n'
        'end tell\n'
        'return n & "\n" & t'
    )
    out = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=3).stdout
    parts = out.rstrip("\n").split("\n", 1)
    return WindowInfo(process=parts[0], title=parts[1] if len(parts) > 1 else "")


def _active_window_linux() -> WindowInfo:
    wid = subprocess.run(["xdotool", "getactivewindow"], capture_output=True, text=True, timeout=3).stdout.strip()
    if not wid:
        return WindowInfo()
    title = subprocess.run(["xdotool", "getwindowname", wid], capture_output=True, text=True, timeout=3).stdout.strip()
    pid = subprocess.run(["xdotool", "getwindowpid", wid], capture_output=True, text=True, timeout=3).stdout.strip()
    return WindowInfo(title=title, process=_process_name(int(pid)) if pid.isdigit() else "")


def get_active_window() -> WindowInfo:
    try:
        if SYSTEM == "Windows":
            return _active_window_windows()
        if SYSTEM == "Darwin":
            return _active_window_macos()
        return _active_window_linux()
    except Exception:
        return WindowInfo()


def get_idle_seconds() -> Optional[float]:
    """距离上次键盘/鼠标操作的秒数；不支持的平台返回 None。"""
    try:
        if SYSTEM == "Windows":
            import ctypes

            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

            info = LASTINPUTINFO()
            info.cbSize = ctypes.sizeof(info)
            if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
                millis = ctypes.windll.kernel32.GetTickCount() - info.dwTime
                return millis / 1000.0
        elif SYSTEM == "Darwin":
            out = subprocess.run(["ioreg", "-c", "IOHIDSystem"], capture_output=True, text=True, timeout=3).stdout
            for line in out.splitlines():
                if "HIDIdleTime" in line:
                    return int(line.split("=")[-1].strip()) / 1e9
        else:
            out = subprocess.run(["xprintidle"], capture_output=True, text=True, timeout=3).stdout.strip()
            if out.isdigit():
                return int(out) / 1000.0
    except Exception:
        pass
    return None


def running_process_names() -> set:
    if psutil is None:
        return set()
    names = set()
    for p in psutil.process_iter(["name"]):
        name = (p.info.get("name") or "").lower()
        if name:
            names.add(name)
    return names
