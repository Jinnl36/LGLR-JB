"""用 Claude 看双屏截图，判断在学习还是在玩；结束时总结“学到了什么”。"""

import base64
import json
import os
from dataclasses import dataclass
from typing import List, Optional

import anthropic

from .capture import ScreenShot

FALLBACK_BETA = "server-side-fallback-2026-07-01"

SCREEN_SYSTEM = """你是一个学习专注度监督助手。用户开启了“学习模式”，你会收到用户电脑上每一块屏幕的截图，以及当前前台（正在操作的）窗口信息。
请判断用户此刻主要在做什么，只能选一个类别：
- study：在学习/工作（看课程、读资料或 PDF、写代码、写作业、做笔记、查资料、背单词等）
- game：在玩游戏（包括游戏画面、游戏启动器、游戏商店、对局大厅）
- entertainment：在娱乐（短视频、与学习无关的视频/直播、社交媒体闲逛、购物、聊天闲聊）
- idle：屏幕上没有有效活动（锁屏、桌面、屏保）
- other：无法判断或其他
判断规则：
1. 以前台窗口所在的屏幕为主；如果另一块屏幕在放游戏/直播/娱乐视频且明显在被观看，也算分心。
2. 学习类视频（课程、讲座、教程）算 study，即使在 B 站或 YouTube 上。
3. study_content 用中文具体写出正在学的知识点（例如“线性代数：矩阵特征值的求法”），不是学习则留空字符串。
4. 只描述屏幕内容，不要编造看不到的东西。"""

SCREEN_SCHEMA = {
    "type": "object",
    "properties": {
        "activity": {"type": "string", "enum": ["study", "game", "entertainment", "idle", "other"]},
        "confidence": {"type": "number", "description": "0 到 1 之间的把握程度"},
        "screens": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "screen": {"type": "integer"},
                    "description": {"type": "string"},
                },
                "required": ["screen", "description"],
                "additionalProperties": False,
            },
        },
        "study_content": {"type": "string"},
        "reason": {"type": "string"},
    },
    "required": ["activity", "confidence", "screens", "study_content", "reason"],
    "additionalProperties": False,
}

SUMMARY_SYSTEM = """你是用户的学习教练。根据一次“学习模式”期间的统计数据和每隔一段时间对屏幕的观察记录，用中文写一份学习总结（Markdown 格式），包含：
1. **一句话总评**（专注度如何）
2. **这次学到了什么**：按主题归纳具体知识点，不要编造观察记录里没有的内容；如果几乎没学习，直接说明
3. **分心情况**：什么时候、因为什么分心（游戏/视频等），持续多久
4. **下次的改进建议**：2~3 条，具体可执行
语气像一个靠谱的朋友，直接、不说教。"""


@dataclass
class ScreenVerdict:
    activity: str
    confidence: float
    screens: List[dict]
    study_content: str
    reason: str


API_KEY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "api_key.txt")


def _make_client() -> anthropic.Anthropic:
    """优先用环境变量 ANTHROPIC_API_KEY；没有的话读项目目录下的 api_key.txt
    （双击 start_mac.command 启动时不一定能读到 ~/.zshrc 里的环境变量）。"""
    if not os.environ.get("ANTHROPIC_API_KEY") and os.path.exists(API_KEY_FILE):
        with open(API_KEY_FILE, encoding="utf-8") as f:
            key = f.read().strip()
        if key:
            return anthropic.Anthropic(api_key=key)
    return anthropic.Anthropic()


class ClaudeAnalyzer:
    def __init__(self, model: str):
        self.client = _make_client()
        self.model = model

    def analyze_screens(self, shots: List[ScreenShot], active_window: str) -> Optional[ScreenVerdict]:
        content = []
        for shot in shots:
            content.append({"type": "text", "text": f"第 {shot.index} 块屏幕："})
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": base64.standard_b64encode(shot.jpeg).decode("ascii"),
                },
            })
        content.append({
            "type": "text",
            "text": f"共 {len(shots)} 块屏幕。当前前台窗口：{active_window or '未知'}。请给出判断。",
        })

        response = self.client.beta.messages.create(
            model=self.model,
            max_tokens=4000,
            system=SCREEN_SYSTEM,
            messages=[{"role": "user", "content": content}],
            output_config={
                "effort": "low",
                "format": {"type": "json_schema", "schema": SCREEN_SCHEMA},
            },
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
        if response.stop_reason in ("refusal", "max_tokens"):
            return None
        text = "".join(b.text for b in response.content if b.type == "text")
        data = json.loads(text)
        return ScreenVerdict(
            activity=data["activity"],
            confidence=float(data["confidence"]),
            screens=data["screens"],
            study_content=data["study_content"],
            reason=data["reason"],
        )

    def summarize_session(self, session_digest: str) -> Optional[str]:
        response = self.client.beta.messages.create(
            model=self.model,
            max_tokens=16000,
            system=SUMMARY_SYSTEM,
            messages=[{"role": "user", "content": session_digest}],
            output_config={"effort": "medium"},
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
        if response.stop_reason == "refusal":
            return None
        return "".join(b.text for b in response.content if b.type == "text").strip() or None
