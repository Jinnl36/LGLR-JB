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

## 安装和启动（Mac）

1. **装 Python**：从 https://www.python.org/downloads/macos/ 下载安装包装好（自带图形界面库）。
   用 Homebrew 装的 Python 还要执行一次 `brew install python-tk`。
2. **填 Claude API Key**（在 https://console.anthropic.com 申请）：在项目文件夹里新建 `api_key.txt`，把 key（`sk-ant-...`）粘进去保存。
   没有 key 也能用，只是只按窗口标题判断，报告里“学到了什么”会改为列出学习时用得最多的窗口。
3. **双击 `start_mac.command`**。第一次会自动安装依赖，然后弹出窗口。
   如果提示“无法验证开发者”，右键 → 打开 → 打开。
4. **授予权限**（只需一次，授给「终端」）：系统设置 → 隐私与安全性 →
   - **屏幕与系统录音**：勾选「终端」（没有这个权限，截图只能拍到桌面壁纸）
   - **辅助功能**：打开「终端」（没有这个权限拿不到窗口标题）
   - **自动化**：允许「终端」控制「System Events」

   改完权限后要**完全退出终端（⌘Q）再重新打开**。程序启动时会自动检查，缺哪个会弹窗提醒。

也可以在终端里手动运行：

```bash
cd 项目文件夹
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
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
| `game_keywords` / `entertainment_keywords` / `study_keywords` | 见代码 | 窗口标题或程序名包含这些词就归为对应类别（游戏 > 娱乐 > 学习） |
| `study_apps` | 见代码 | 程序名完全一致就算学习（如 Code、Xcode、预览、备忘录、终端）。Mac 上很多软件的窗口标题不带软件名，靠这个识别 |

## 其他系统

- **Windows**：也能用。装好 Python 后执行 `pip install -r requirements.txt`、`python -m study_monitor`，不需要额外权限。
- **Linux（X11）**：需要额外安装 `xdotool`（获取前台窗口）和 `xprintidle`（空闲时间）。

## 隐私

- 截图只在内存里压缩后发给 Claude API 分析，默认**不保存到硬盘**。
- 开启 AI 分析后，屏幕内容会发送到 Anthropic 的 API。不想上传的话，把 `ai_interval_sec` 设为 0。
- 费用参考：每 60 秒分析一次双屏，学习 1 小时大约分析 60 次。想更省钱可以调大间隔或缩小截图宽度。
