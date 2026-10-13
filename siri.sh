#!/bin/bash
# 给 Mac「快捷指令」/ Siri 调用：./siri.sh start | stop | status
cd "$(dirname "$0")" || exit 1
PY=.venv/bin/python
[ -x "$PY" ] || PY=python3
exec "$PY" -m study_monitor "$@"
