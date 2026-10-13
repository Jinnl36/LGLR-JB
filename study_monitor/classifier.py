"""基于窗口标题 / 进程名的规则判断（不联网，随时可用）。"""

from .config import Config
from .system_info import WindowInfo

STUDY = "study"
GAME = "game"
ENTERTAINMENT = "entertainment"
IDLE = "idle"
OTHER = "other"

LABELS = {
    STUDY: "认真学习",
    GAME: "打游戏",
    ENTERTAINMENT: "刷视频/娱乐",
    IDLE: "离开/发呆",
    OTHER: "其他/未识别",
}

# 计入“分心”的类别
DISTRACTED = {GAME, ENTERTAINMENT, IDLE}


def _match(text: str, keywords) -> str:
    for kw in keywords:
        if kw.lower() in text:
            return kw
    return ""


def classify_window(window: WindowInfo, cfg: Config) -> tuple:
    """返回 (类别, 命中的关键词)。游戏优先级最高：标题里同时有“学习”和“原神”也算游戏。"""
    text = window.text().lower()
    if not text:
        return OTHER, ""
    kw = _match(text, cfg.game_keywords)
    if kw:
        return GAME, kw
    kw = _match(text, cfg.entertainment_keywords)
    if kw:
        return ENTERTAINMENT, kw
    kw = _match(text, cfg.study_keywords)
    if kw:
        return STUDY, kw
    process = window.process.lower()
    if process and process in {a.lower() for a in cfg.study_apps}:
        return STUDY, window.process
    return OTHER, ""
