# 学习监督器

打开“学习模式”后开始计时，同时盯着你的**两块屏幕**，分辨你是在认真学习，还是在打游戏或刷视频。
结束学习模式时会生成一份报告，写明：

- **总时长 / 真正学习了多久 / 分心了多久**（打游戏、刷视频、离开电脑分别多久）
- **这次学到了什么**：Claude 根据学习期间看到的屏幕内容，按知识点归纳
- **什么时候分心、因为什么分心**，以及下次的改进建议

## 工作原理

| 信号 | 频率 | 作用 |
|---|---|---|
| 前台窗口标题 + 进程名 | 每 5 秒 | 用关键词粗判（Steam、英雄联盟、原神 → 游戏；VS Code、PDF、慕课 → 学习），负责精确计时 |
| 键盘鼠标空闲时间 | 每 5 秒 | 超过 3 分钟没操作 → 算“离开/发呆” |
| **两块屏幕的截图 → Claude** | 每 60 秒 | 看画面判断真实在做什么（比如 B 站上看的是课程还是游戏直播；副屏有没有在放视频），并记下“正在学的知识点” |

AI 判断会修正规则判断：规则认不出的窗口交给 AI 定；前台一直是同一个学习窗口、但副屏在放直播或游戏，这段时间也会算成分心。

## 安装

需要 Python 3.10 及以上（Windows 安装 Python 时请勾选 tcl/tk，默认就会勾选）。

```bash
pip install -r requirements.txt
```

配置 Claude API Key（在 https://console.anthropic.com 申请）：

```bash
# Windows PowerShell
setx ANTHROPIC_API_KEY "sk-ant-..."
# macOS / Linux
export ANTHROPIC_API_KEY="sk-ant-..."
```

没有 API Key 也能用：只按窗口标题判断，报告里“学到了什么”会改为列出学习时用得最多的窗口。

## 使用

```bash
python -m study_monitor          # 打开窗口，点「开始学习模式」/「结束学习模式」
python -m study_monitor --cli    # 命令行模式，Ctrl+C 结束
python -m study_monitor --init   # 生成 config.json，可自定义关键词和频率
```

报告保存在 `reports/学习报告_日期_时间.md`，同名的 `.json` 文件是原始计时数据。

## 自定义（config.json）

| 字段 | 默认 | 说明 |
|---|---|---|
| `sample_interval_sec` | 5 | 多久检查一次前台窗口 |
| `ai_interval_sec` | 60 | 多久截一次屏交给 Claude；设为 0 关闭 AI |
| `idle_threshold_sec` | 180 | 无操作多久算离开 |
| `model` | `claude-opus-5-5` | 使用的 Claude 模型 |
| `screenshot_max_width` | 1280 | 截图缩放宽度，越小越省钱 |
| `save_screenshots` | false | 是否把截图存到 `reports/screenshots/` |
| `game_keywords` / `entertainment_keywords` / `study_keywords` | 见代码 | 窗口标题或进程名包含这些词就归为对应类别（游戏 > 娱乐 > 学习） |

## 各平台说明

- **Windows**：开箱即用（前台窗口和空闲时间检测都支持）。
- **macOS**：首次运行需在「系统设置 → 隐私与安全性」里给终端开启**屏幕录制**和**辅助功能**权限。
- **Linux（X11）**：需要安装 `xdotool`（获取前台窗口）和 `xprintidle`（空闲时间）。

## 隐私

- 截图只在内存里压缩后发给 Claude API 分析，默认**不保存到硬盘**。
- 开启 AI 分析后，屏幕内容会发送到 Anthropic 的 API。不想上传的话，把 `ai_interval_sec` 设为 0。
- 费用参考：每 60 秒分析一次双屏，学习 1 小时大约分析 60 次。想更省钱可以调大间隔或缩小截图宽度。
