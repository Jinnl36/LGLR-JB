#!/bin/bash
# 双击运行：第一次会自动创建虚拟环境并安装依赖
cd "$(dirname "$0")" || exit 1

if ! command -v python3 >/dev/null 2>&1; then
  echo "没有找到 python3，请先安装：https://www.python.org/downloads/macos/"
  read -r -p "按回车退出"; exit 1
fi
if ! python3 -c "import tkinter" 2>/dev/null; then
  echo "当前 Python 缺少图形界面库 tkinter。"
  echo "用 Homebrew 装的 Python 请执行：brew install python-tk"
  echo "或者从 python.org 下载安装包（自带 tkinter）。"
  read -r -p "按回车退出"; exit 1
fi

if [ ! -d .venv ]; then
  echo "首次运行，正在安装依赖…"
  python3 -m venv .venv || exit 1
fi
source .venv/bin/activate
pip install -q -r requirements.txt || { read -r -p "依赖安装失败，按回车退出"; exit 1; }

python -m study_monitor
