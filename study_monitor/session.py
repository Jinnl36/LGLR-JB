"""学习模式会话：后台持续计时、分类、定时调用 AI 看屏幕。"""

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List, Optional

import anthropic

from . import classifier as C
from .config import Config
from .system_info import WindowInfo, check_macos_permissions, get_active_window, get_idle_seconds

# AI 判断的把握度高于这个值时，覆盖规则判断
AI_OVERRIDE_CONFIDENCE = 0.6


@dataclass
class Tick:
    start: float
    end: float
    window: WindowInfo
    rule_category: str
    category: str
    keyword: str = ""

    @property
    def seconds(self) -> float:
        return self.end - self.start


@dataclass
class AISample:
    time: float
    window: str
    activity: str
    confidence: float
    study_content: str
    reason: str
    screens: List[dict] = field(default_factory=list)


class StudySession:
    def __init__(self, cfg: Config, on_update: Optional[Callable[[], None]] = None):
        self.cfg = cfg
        self.on_update = on_update
        self.ticks: List[Tick] = []
        self.ai_samples: List[AISample] = []
        self.errors: List[str] = []
        self.started_at: float = 0.0
        self.ended_at: float = 0.0
        self.current_window = WindowInfo()
        self.current_category = C.OTHER
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._ai_threads: List[threading.Thread] = []
        self._analyzer = None
        self._last_ai_time = 0.0
        self._ai_busy = False

        self.errors.extend(check_macos_permissions())
        if cfg.ai_interval_sec > 0:
            try:
                from .ai_analyzer import ClaudeAnalyzer
                self._analyzer = ClaudeAnalyzer(cfg.model)
            except Exception as e:  # 没装 anthropic / 没配置 API key：降级为规则模式
                self.errors.append(f"AI 分析未启用：{e}")

    @property
    def ai_enabled(self) -> bool:
        return self._analyzer is not None

    # ---------- 生命周期 ----------
    def start(self) -> None:
        self.started_at = time.time()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=10)
        # 等待还在进行中的 AI 分析（最多 60 秒）
        for t in self._ai_threads:
            t.join(timeout=60)
        self.ended_at = time.time()

    # ---------- 主循环 ----------
    def _run(self) -> None:
        last = time.time()
        self._sample(last, last)
        while not self._stop.wait(self.cfg.sample_interval_sec):
            now = time.time()
            self._sample(last, now)
            last = now
        self._sample(last, time.time())

    def _sample(self, start: float, end: float) -> None:
        window = get_active_window()
        idle = get_idle_seconds()
        if idle is not None and idle >= self.cfg.idle_threshold_sec:
            category, kw = C.IDLE, ""
        else:
            category, kw = C.classify_window(window, self.cfg)
        with self._lock:
            if end > start:
                self.ticks.append(Tick(start, end, window, category, category, kw))
            self.current_window = window
            self.current_category = category

        if self.ai_enabled and not self._ai_busy and not self._stop.is_set() \
                and end - self._last_ai_time >= self.cfg.ai_interval_sec:
            self._ai_busy = True
            t = threading.Thread(target=self._run_ai, args=(window, self._last_ai_time), daemon=True)
            self._ai_threads.append(t)
            t.start()
        self._notify()

    def _run_ai(self, window: WindowInfo, prev_ai_time: float) -> None:
        from .capture import capture_all_screens
        sample_time = time.time()
        self._last_ai_time = sample_time
        try:
            shots = capture_all_screens(self.cfg.screenshot_max_width)
            if self.cfg.save_screenshots:
                self._save_shots(shots, sample_time)
            verdict = self._analyzer.analyze_screens(shots, window.text())
            if verdict is None:
                return
            sample = AISample(sample_time, window.text(), verdict.activity, verdict.confidence,
                              verdict.study_content, verdict.reason, verdict.screens)
            with self._lock:
                self.ai_samples.append(sample)
                self._apply_ai(sample, prev_ai_time or self.started_at)
        except anthropic.APIError as e:
            self.errors.append(f"{datetime.now():%H:%M:%S} Claude 调用失败：{e}")
        except Exception as e:
            self.errors.append(f"{datetime.now():%H:%M:%S} 截图/分析失败：{e}")
        finally:
            self._ai_busy = False
            self._notify()

    def _apply_ai(self, sample: AISample, since: float) -> None:
        """AI 看到的画面修正从上次 AI 采样到这次之间的计时片段。

        只修正两种片段：规则认不出的（other），以及前台窗口和截图时相同的
        （例如前台一直是 VS Code，但另一块屏幕在放直播 → 这段算分心）。
        前台换过窗口的片段保留规则判断，避免一次截图改写整段时间。"""
        if sample.activity in (C.IDLE, C.OTHER) or sample.confidence < AI_OVERRIDE_CONFIDENCE:
            return
        for tick in self.ticks:
            if tick.end <= since or tick.start > sample.time or tick.rule_category == C.IDLE:
                continue
            if tick.rule_category == C.OTHER or tick.window.text() == sample.window:
                tick.category = sample.activity
        self.current_category = sample.activity if self.current_category != C.IDLE else C.IDLE

    def _save_shots(self, shots, sample_time: float) -> None:
        import os
        folder = os.path.join(self.cfg.report_dir, "screenshots",
                              datetime.fromtimestamp(self.started_at).strftime("%Y%m%d_%H%M%S"))
        os.makedirs(folder, exist_ok=True)
        stamp = datetime.fromtimestamp(sample_time).strftime("%H%M%S")
        for s in shots:
            with open(os.path.join(folder, f"{stamp}_screen{s.index}.jpg"), "wb") as f:
                f.write(s.jpeg)

    def _notify(self) -> None:
        if self.on_update:
            try:
                self.on_update()
            except Exception:
                pass

    # ---------- 统计 ----------
    def totals(self) -> dict:
        with self._lock:
            totals = defaultdict(float)
            for t in self.ticks:
                totals[t.category] += t.seconds
        return dict(totals)

    def elapsed(self) -> float:
        return (self.ended_at or time.time()) - self.started_at

    def top_windows(self, category: str, n: int = 8) -> List[tuple]:
        acc = defaultdict(float)
        with self._lock:
            for t in self.ticks:
                if t.category == category:
                    acc[t.window.title or t.window.process or "(未知窗口)"] += t.seconds
        return sorted(acc.items(), key=lambda kv: -kv[1])[:n]

    def distraction_periods(self, min_seconds: float = 30) -> List[tuple]:
        """连续分心的时间段：(开始, 结束, 类别, 窗口)。"""
        periods = []
        with self._lock:
            ticks = list(self.ticks)
        cur = None
        for t in ticks:
            if t.category in C.DISTRACTED:
                if cur and cur[2] == t.category and abs(cur[1] - t.start) < 1:
                    cur[1] = t.end
                else:
                    if cur:
                        periods.append(tuple(cur))
                    cur = [t.start, t.end, t.category, t.window.title or t.window.process]
            elif cur:
                periods.append(tuple(cur))
                cur = None
        if cur:
            periods.append(tuple(cur))
        return [p for p in periods if p[1] - p[0] >= min_seconds]
