"""入口：python -m study_monitor            图形界面
        python -m study_monitor start      开始学习模式（程序没开会先打开）—— 给 Siri / 快捷指令用
        python -m study_monitor stop       结束学习模式，打印本次统计
        python -m study_monitor status     查看当前进度
        python -m study_monitor --cli      命令行模式（Ctrl+C 结束学习模式）
        python -m study_monitor --init     生成可编辑的 config.json"""

import argparse
import os
import platform
import subprocess
import sys
import time

from .config import CONFIG_PATH, load_config, save_default_config


def run_cli():
    from . import classifier as C
    from .app import finish_session
    from .report import fmt_duration
    from .session import StudySession

    session = StudySession(load_config())
    session.start()
    print("学习模式已开始（AI 分析：%s）。按 Ctrl+C 结束。" % ("开" if session.ai_enabled else "关"))
    try:
        while True:
            time.sleep(10)
            totals = session.totals()
            print(f"[{fmt_duration(session.elapsed())}] 学习 {fmt_duration(totals.get(C.STUDY, 0))}"
                  f" ｜ 分心 {fmt_duration(sum(totals.get(k, 0) for k in C.DISTRACTED))}"
                  f" ｜ 当前：{C.LABELS[session.current_category]}")
    except KeyboardInterrupt:
        print("\n正在结束并生成学习总结…")
    path = finish_session(session)
    print(open(path, encoding="utf-8").read())
    print(f"\n报告已保存：{path}")


def remote(cmd: str) -> None:
    from .control import AUTOSTART_FLAG, PROJECT_DIR, send_command

    reply = send_command(cmd)
    if reply is not None:
        print(reply)
        return
    if cmd != "start":
        print("学习监督器没有在运行，现在没有在学习模式中。")
        return
    # 程序没开：留个自动开始标记，再把程序打开
    with open(AUTOSTART_FLAG, "w") as f:
        f.write("1")
    if platform.system() == "Darwin":
        # 通过「终端」打开，这样用的是已经授予终端的屏幕录制 / 辅助功能权限
        subprocess.Popen(["open", os.path.join(PROJECT_DIR, "start_mac.command")])
    else:
        subprocess.Popen([sys.executable, "-m", "study_monitor"], cwd=PROJECT_DIR)
    print("正在打开学习监督器，学习模式马上开始，加油！")


def main():
    parser = argparse.ArgumentParser(description="学习监督器：学习模式下监控双屏，统计真正学习与分心时间")
    parser.add_argument("command", nargs="?", choices=["start", "stop", "status"],
                        help="遥控正在运行的程序：start 开始 / stop 结束 / status 查看进度")
    parser.add_argument("--cli", action="store_true", help="不用图形界面，在命令行运行")
    parser.add_argument("--init", action="store_true", help="生成默认 config.json 后退出")
    args = parser.parse_args()
    if args.command:
        remote(args.command)
    elif args.init:
        save_default_config()
        print(f"已生成配置文件：{CONFIG_PATH}")
    elif args.cli:
        run_cli()
    else:
        from .control import send_command
        if send_command("status") is not None:  # 已经开着一个了，不重复打开
            print("学习监督器已经在运行。")
            return
        from .app import run_gui
        run_gui()


if __name__ == "__main__":
    main()
