"""结束学习模式后生成报告（Markdown + 原始数据 JSON）。"""

import json
import os
from dataclasses import asdict
from datetime import datetime
from typing import Optional

from . import classifier as C
from .session import StudySession


def fmt_duration(seconds: float) -> str:
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h} 小时 {m} 分"
    if m:
        return f"{m} 分 {s} 秒"
    return f"{s} 秒"


def _clock(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S")


def build_digest(session: StudySession) -> str:
    """给 Claude 写总结用的会话摘要。"""
    totals = session.totals()
    lines = [
        f"学习模式时间：{_clock(session.started_at)} - {_clock(session.ended_at)}，共 {fmt_duration(session.elapsed())}",
        "各类时间：" + "，".join(f"{C.LABELS[k]} {fmt_duration(v)}" for k, v in totals.items()),
        "",
        "## 学习时最常用的窗口",
    ]
    lines += [f"- {title}（{fmt_duration(sec)}）" for title, sec in session.top_windows(C.STUDY)]
    lines += ["", "## 分心时间段"]
    lines += [f"- {_clock(a)}-{_clock(b)} {C.LABELS[cat]}：{win}" for a, b, cat, win in session.distraction_periods()]
    lines += ["", "## 定时屏幕观察记录（时间 / 判断 / 在学的内容 / 理由）"]
    for s in session.ai_samples:
        lines.append(f"- {_clock(s.time)} [{C.LABELS.get(s.activity, s.activity)}] "
                     f"{s.study_content or '-'} ｜ {s.reason}")
    return "\n".join(lines)


def _fallback_learned(session: StudySession) -> str:
    """没有 AI 时，用学习窗口标题粗略列出学了什么。"""
    items = session.top_windows(C.STUDY, n=10)
    if not items:
        return "这次没有检测到学习类窗口。"
    return "（未启用 AI 总结，以下是学习期间用得最多的窗口，可据此回忆学了什么）\n\n" + \
        "\n".join(f"- {title}（{fmt_duration(sec)}）" for title, sec in items)


def write_report(session: StudySession, ai_summary: Optional[str]) -> str:
    totals = session.totals()
    total = session.elapsed()
    study = totals.get(C.STUDY, 0.0)
    distracted = sum(totals.get(k, 0.0) for k in C.DISTRACTED)
    other = totals.get(C.OTHER, 0.0)
    focus_rate = study / total * 100 if total else 0

    start = datetime.fromtimestamp(session.started_at)
    md = [
        f"# 学习模式报告 · {start:%Y-%m-%d %H:%M}",
        "",
        f"**时间段**：{start:%H:%M:%S} - {_clock(session.ended_at)}　**总时长**：{fmt_duration(total)}",
        "",
        "| 项目 | 时长 | 占比 |",
        "|---|---|---|",
        f"| ✅ 真正学习 | **{fmt_duration(study)}** | {focus_rate:.0f}% |",
        f"| ❌ 分心合计 | **{fmt_duration(distracted)}** | {distracted / total * 100 if total else 0:.0f}% |",
    ]
    for key in (C.GAME, C.ENTERTAINMENT, C.IDLE):
        if totals.get(key):
            md.append(f"| 　└ {C.LABELS[key]} | {fmt_duration(totals[key])} | {totals[key] / total * 100:.0f}% |")
    md.append(f"| ❔ 其他/未识别 | {fmt_duration(other)} | {other / total * 100 if total else 0:.0f}% |")

    md += ["", "## 学到了什么", "", ai_summary or _fallback_learned(session), ""]

    periods = session.distraction_periods()
    md += ["## 分心记录", ""]
    if periods:
        md += [f"- {_clock(a)} - {_clock(b)}（{fmt_duration(b - a)}）{C.LABELS[cat]}：{win}" for a, b, cat, win in periods]
    else:
        md.append("没有超过 30 秒的连续分心，很棒！")

    if session.ai_samples:
        md += ["", "## 屏幕观察时间线", "", "| 时间 | 判断 | 在学什么 | 说明 |", "|---|---|---|---|"]
        for s in session.ai_samples:
            md.append(f"| {_clock(s.time)} | {C.LABELS.get(s.activity, s.activity)} | "
                      f"{s.study_content or '-'} | {s.reason.replace('|', '/')} |")

    if session.errors:
        md += ["", "## 运行提示", ""] + [f"- {e}" for e in session.errors[-10:]]

    os.makedirs(session.cfg.report_dir, exist_ok=True)
    base = os.path.join(session.cfg.report_dir, f"学习报告_{start:%Y%m%d_%H%M%S}")
    path = base + ".md"
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump({
            "started_at": session.started_at,
            "ended_at": session.ended_at,
            "totals_sec": totals,
            "ticks": [{"start": t.start, "end": t.end, "title": t.window.title, "process": t.window.process,
                       "rule_category": t.rule_category, "category": t.category} for t in session.ticks],
            "ai_samples": [asdict(s) for s in session.ai_samples],
        }, f, ensure_ascii=False, indent=2)
    return path
