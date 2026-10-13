"""配置：读取 config.json（不存在时使用默认值）。"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import List

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")


def _default_game_keywords() -> List[str]:
    return [
        # 平台 / 启动器
        "steam", "epic games", "wegame", "battle.net", "ea app", "ubisoft", "riot client",
        # 常见游戏（窗口标题或进程名的一部分，忽略大小写）
        "league of legends", "英雄联盟", "valorant", "无畏契约", "counter-strike", "cs2", "csgo",
        "dota", "原神", "genshin", "崩坏", "星穹铁道", "starrail", "绝区零", "zenless",
        "minecraft", "我的世界", "王者荣耀", "和平精英", "pubg", "绝地求生", "apex",
        "fortnite", "overwatch", "守望先锋", "魔兽", "warcraft", "炉石", "hearthstone",
        "永劫无间", "naraka", "穿越火线", "crossfire", "地下城与勇士", "dnf", "leagueclient",
        "elden ring", "艾尔登法环", "黑神话", "wukong", "roblox", "terraria", "4399",
        "棋牌", "斗地主", "欢乐麻将",
    ]


def _default_entertainment_keywords() -> List[str]:
    return [
        "抖音", "douyin", "tiktok", "快手", "kuaishou", "微博", "weibo", "小红书", "xiaohongshu",
        "netflix", "爱奇艺", "iqiyi", "腾讯视频", "优酷", "youku", "芒果tv", "twitch", "虎牙",
        "斗鱼", "huya", "douyu", "直播", "番剧", "综艺", "电视剧", "游戏解说",
    ]


def _default_study_keywords() -> List[str]:
    return [
        # 编程 / 写作 / 笔记
        "visual studio", "vs code", "vscode", "pycharm", "intellij", "clion", "webstorm", "jupyter",
        "terminal", "终端", "powershell", "cmd.exe", "notion", "obsidian", "onenote", "typora",
        "microsoft word", "- word", "excel", "powerpoint", "wps", "latex", "overleaf", "xmind", "goodnotes",
        # 学习资料 / 网站
        ".pdf", "acrobat", "pdf", "zotero", "anki", "知乎专栏", "csdn", "leetcode", "力扣",
        "github", "stack overflow", "stackoverflow", "mooc", "慕课", "coursera", "edx", "khan",
        "学堂在线", "网易公开课", "中国大学", "wikipedia", "维基", "百度百科", "chatgpt", "claude",
        "课程", "教程", "讲义", "作业", "笔记", "学习", "lecture", "tutorial", "course", "homework",
        "词典", "dictionary", "translate", "翻译", "百词斩", "不背单词", "扇贝",
        # macOS 软件
        "xcode", "iterm", "keynote", "marginnote", "notability", "pdf expert", "skim", "欧路词典",
    ]


def _default_study_apps() -> List[str]:
    """按进程名「完全一致」匹配的学习软件（不区分大小写）。
    macOS 上很多软件的窗口标题不带软件名（比如 VS Code 只显示文件名），所以按进程名认。"""
    return [
        "code", "cursor", "xcode", "terminal", "终端", "iterm2", "pycharm", "idea", "goland",
        "preview", "预览", "notes", "备忘录", "pages", "numbers", "keynote", "microsoft word",
        "microsoft excel", "microsoft powerpoint", "wps office", "notion", "obsidian", "anki",
        "zotero", "marginnote 3", "marginnote 4", "goodnotes", "notability", "dictionary", "词典",
    ]


@dataclass
class Config:
    # 每隔多少秒检查一次当前前台窗口（用于计时，越小越精确）
    sample_interval_sec: int = 5
    # 每隔多少秒截一次双屏图交给 Claude 分析（0 = 关闭 AI 分析，只用规则判断）
    ai_interval_sec: int = 60
    # 键鼠无操作超过多少秒算“离开/发呆”（仅 Windows 支持检测）
    idle_threshold_sec: int = 180
    # Claude 模型
    model: str = "claude-opus-5-5"
    # 截图发给 AI 前缩放到的最大宽度（越小越省钱）
    screenshot_max_width: int = 1280
    # 是否把截图保存到报告目录（默认不保存，只在内存里用完即丢）
    save_screenshots: bool = False
    # 报告输出目录
    report_dir: str = "reports"
    game_keywords: List[str] = field(default_factory=_default_game_keywords)
    entertainment_keywords: List[str] = field(default_factory=_default_entertainment_keywords)
    study_keywords: List[str] = field(default_factory=_default_study_keywords)
    study_apps: List[str] = field(default_factory=_default_study_apps)


def load_config(path: str = CONFIG_PATH) -> Config:
    cfg = Config()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key, value in data.items():
            if hasattr(cfg, key):
                setattr(cfg, key, value)
    return cfg


def save_default_config(path: str = CONFIG_PATH) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(Config()), f, ensure_ascii=False, indent=2)
