"""截取所有显示器（两块屏幕各一张）。"""

import io
from dataclasses import dataclass
from typing import List

import mss
from PIL import Image


@dataclass
class ScreenShot:
    index: int          # 第几块屏幕（从 1 开始）
    jpeg: bytes         # 压缩后的 JPEG
    width: int
    height: int


def capture_all_screens(max_width: int = 1280, quality: int = 70) -> List[ScreenShot]:
    shots = []
    with mss.mss() as sct:
        # monitors[0] 是所有屏幕拼起来的虚拟大屏，[1:] 才是每块物理屏幕
        for i, monitor in enumerate(sct.monitors[1:], start=1):
            raw = sct.grab(monitor)
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
            if img.width > max_width:
                ratio = max_width / img.width
                img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality)
            shots.append(ScreenShot(index=i, jpeg=buf.getvalue(), width=img.width, height=img.height))
    return shots
