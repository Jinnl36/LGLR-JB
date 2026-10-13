"""入口：python -m study_monitor            图形界面
        python -m study_monitor --cli      命令行模式（Ctrl+C 结束学习模式）
        python -m study_monitor --init     生成可编辑的 config.json"""

import argparse
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


def main():
    parser = argparse.ArgumentParser(description="学习监督器：学习模式下监控双屏，统计真正学习与分心时间")
    parser.add_argument("--cli", action="store_true", help="不用图形界面，在命令行运行")
    parser.add_argument("--init", action="store_true", help="生成默认 config.json 后退出")
    args = parser.parse_args()
    if args.init:
        save_default_config()
        print(f"已生成配置文件：{CONFIG_PATH}")
    elif args.cli:
        run_cli()
    else:
        from .app import run_gui
        run_gui()


if __name__ == "__main__":
    main()
