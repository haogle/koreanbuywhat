#!/usr/bin/env bash
#
# rerun.sh — 一键重跑某一周的飞书推送（补完映射后用）
#
#   ./rerun.sh                    # 跑上一交易周
#   ./rerun.sh 20260727 20260731  # 跑指定周
#
# 凭证优先从环境变量读；本地没设时回退到同目录 .env（KEY=VALUE 格式）。
set -euo pipefail

cd "$(dirname "$0")"

# 若环境变量缺失，尝试从 .env 载入
if [ -z "${FEISHU_WEBHOOK:-}" ] && [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

for var in FEISHU_WEBHOOK FEISHU_APP_ID FEISHU_APP_SECRET; do
  if [ -z "${!var:-}" ]; then
    echo "❌ 缺少环境变量 $var"
    echo "   请 export，或在 $(pwd)/.env 里写 $var=..."
    exit 1
  fi
done

if [ $# -eq 2 ]; then
  echo "▶ 重跑 $1 ~ $2"
  exec python3 notify_feishu.py "$1" "$2"
elif [ $# -eq 0 ]; then
  echo "▶ 跑上一交易周"
  exec python3 notify_feishu.py
else
  echo "用法: $0 [START_YYYYMMDD END_YYYYMMDD]"
  exit 1
fi
