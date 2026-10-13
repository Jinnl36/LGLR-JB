"""图形界面：一键开始 / 结束学习模式。"""

import os
import platform
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext

from . import classifier as C
from .config import Config, load_config
from .control import ControlServer, consume_autostart_flag
from .report import build_digest, fmt_duration, write_report
from .session import StudySession

# macOS 用苹方，Windows 用微软雅黑
FONT = "PingFang SC" if platform.system() == "Darwin" else "Microsoft YaHei"

COLORS = {
    C.STUDY: "#2e7d32",
    C.GAME: "#c62828",
    C.ENTERTAINMENT: "#ef6c00",
    C.IDLE: "#6d4c41",
    C.OTHER: "#546e7a",
}


def finish_session(session: StudySession) -> str:
    """停止会话、生成 AI 总结、写报告，返回报告路径。"""
    session.stop()
    summary = None
    if session.ai_enabled:
        try:
            summary = session._analyzer.summarize_session(build_digest(session))
        except Exception as e:
            session.errors.append(f"生成学习总结失败：{e}")
    return write_report(session, summary)


def open_path(path: str) -> None:
    try:
        if platform.system() == "Windows":
            os.startfile(path)  # type: ignore[attr-defined]
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


class ColorButton(tk.Label):
    """彩色按钮。macOS 的 tk.Button 会忽略背景色（白字白底看不见），所以用 Label 自己画。"""

    def __init__(self, master, command, **kw):
        super().__init__(master, cursor="hand2", fg="white", **kw)
        self.command = command
        self.enabled = True
        self.bind("<Button-1>", lambda e: self.enabled and self.command())

    def set(self, text: str, color: str, enabled: bool = True):
        self.enabled = enabled
        self.config(text=text, bg=color, cursor="hand2" if enabled else "arrow")


class App:
    def __init__(self, cfg: Config, autostart: bool = False):
        self.cfg = cfg
        self.session = None
        self.root = tk.Tk()
        self.root.title("学习监督器")
        self.root.geometry("480x420")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        font = (FONT, 13)
        self.btn = ColorButton(self.root, self.toggle, font=(FONT, 18, "bold"))
        self.btn.set("▶ 开始学习模式", "#2e7d32")
        self.btn.pack(fill="x", padx=16, pady=(16, 8), ipady=10)

        self.status = tk.Label(self.root, text="未开始", font=(FONT, 16, "bold"), fg="#546e7a")
        self.status.pack(pady=4)
        self.window_label = tk.Label(self.root, text="", font=(FONT, 11), fg="#777", wraplength=420)
        self.window_label.pack()

        grid = tk.Frame(self.root)
        grid.pack(pady=10)
        self.values = {}
        rows = [("total", "已进行"), (C.STUDY, "真正学习"), ("distracted", "分心合计"),
                (C.GAME, "　打游戏"), (C.ENTERTAINMENT, "　刷视频/娱乐"), (C.IDLE, "　离开/发呆"), (C.OTHER, "其他")]
        for r, (key, label) in enumerate(rows):
            tk.Label(grid, text=label, font=font, anchor="w", width=12).grid(row=r, column=0, sticky="w")
            v = tk.Label(grid, text="-", font=font, anchor="e", width=14)
            v.grid(row=r, column=1, sticky="e")
            self.values[key] = v

        self.ai_label = tk.Label(self.root, text="", font=(FONT, 11), fg="#777", wraplength=420)
        self.ai_label.pack(side="bottom", pady=8)
        self.control = ControlServer()
        self.refresh()
        self.poll_commands()
        if autostart or consume_autostart_flag():
            self.root.after(500, self.toggle)

    def toggle(self):
        if self.session is None:
            self.session = StudySession(self.cfg)
            self.session.start()
            self.btn.set("■ 结束学习模式", "#c62828")
            if self.session.errors:
                head = "" if self.session.ai_enabled else "AI 屏幕分析未启用，将只根据窗口标题判断。\n\n"
                # 延后弹窗：弹窗会阻塞界面线程，先让 Siri 的命令拿到回复
                errors = head + "\n\n".join(self.session.errors)
                self.root.after(300, lambda: messagebox.showwarning("提示", errors))
        else:
            session, self.session = self.session, None
            self.btn.set("正在生成学习总结…", "#757575", enabled=False)
            threading.Thread(target=self._finish, args=(session,), daemon=True).start()

    def _finish(self, session):
        path = finish_session(session)
        self.root.after(0, lambda: self._show_report(path))

    def _show_report(self, path):
        self.btn.set("▶ 开始学习模式", "#2e7d32")
        win = tk.Toplevel(self.root)
        win.title("学习报告")
        win.geometry("720x640")
        text = scrolledtext.ScrolledText(win, wrap="word", font=(FONT, 13))
        with open(path, encoding="utf-8") as f:
            text.insert("1.0", f.read())
        text.config(state="disabled")
        text.pack(fill="both", expand=True)
        tk.Button(win, text="打开报告文件夹", command=lambda: open_path(os.path.dirname(os.path.abspath(path)))).pack(pady=6)
        # 报告窗口弹到最前面（用 Siri 结束时，程序可能在后台）
        win.lift()
        win.attributes("-topmost", True)
        win.after(1500, lambda: win.attributes("-topmost", False))
        win.focus_force()

    # ---------- Siri / 快捷指令 / 命令行遥控 ----------
    def poll_commands(self):
        self.control.process_pending(self.handle_command)
        self.root.after(200, self.poll_commands)

    def _stats_sentence(self, s: StudySession) -> str:
        totals = s.totals()
        distracted = sum(totals.get(k, 0) for k in C.DISTRACTED)
        text = f"已进行{fmt_duration(s.elapsed())}，真正学习{fmt_duration(totals.get(C.STUDY, 0))}，分心{fmt_duration(distracted)}"
        if totals.get(C.GAME, 0) >= 60:
            text += f"，其中打游戏{fmt_duration(totals[C.GAME])}"
        return text + "。"

    def handle_command(self, cmd: str) -> str:
        if cmd == "start":
            if self.session is not None:
                return "学习模式已经在进行中。" + self._stats_sentence(self.session)
            if not self.btn.enabled:
                return "上一次的学习报告还在生成，请稍等几秒再试。"
            self.toggle()
            return "学习模式已开始，我会盯着你的屏幕，加油！"
        if cmd == "stop":
            if self.session is None:
                return "现在没有在学习模式中。"
            reply = "学习模式已结束。" + self._stats_sentence(self.session) + "详细的学习总结正在生成，稍后会弹出来。"
            self.toggle()
            return reply
        if cmd == "status":
            if self.session is None:
                return "现在没有在学习模式中。"
            return self._stats_sentence(self.session)
        return f"不认识的命令：{cmd}"

    def refresh(self):
        s = self.session
        if s is not None:
            totals = s.totals()
            distracted = sum(totals.get(k, 0) for k in C.DISTRACTED)
            self.values["total"].config(text=fmt_duration(s.elapsed()))
            self.values["distracted"].config(text=fmt_duration(distracted), fg=COLORS[C.GAME])
            for key in (C.STUDY, C.GAME, C.ENTERTAINMENT, C.IDLE, C.OTHER):
                self.values[key].config(text=fmt_duration(totals.get(key, 0)), fg=COLORS[key])
            cat = s.current_category
            self.status.config(text=f"当前：{C.LABELS[cat]}", fg=COLORS[cat])
            self.window_label.config(text=s.current_window.text()[:120])
            if s.ai_samples:
                last = s.ai_samples[-1]
                self.ai_label.config(text=f"AI 最近观察：{C.LABELS.get(last.activity, last.activity)}"
                                          f"{'｜在学：' + last.study_content if last.study_content else ''}")
            elif s.ai_enabled:
                self.ai_label.config(text="AI 正在观察两块屏幕…")
            if s.errors:
                self.ai_label.config(text=s.errors[-1][:160])
        elif self.btn.enabled:
            self.status.config(text="未开始", fg=COLORS[C.OTHER])
        self.root.after(1000, self.refresh)

    def on_close(self):
        if self.session is not None and not messagebox.askyesno("退出", "学习模式还在进行，确定退出？（不会生成报告）"):
            return
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def run_gui(autostart: bool = False):
    App(load_config(), autostart=autostart).run()
