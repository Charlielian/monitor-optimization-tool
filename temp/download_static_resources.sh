#!/bin/bash
# 下载静态资源脚本
# 在有网络的环境下运行此脚本，将资源下载到本地

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATIC_DIR="$SCRIPT_DIR/static"

# 创建必要的目录
mkdir -p "$STATIC_DIR/css"
mkdir -p "$STATIC_DIR/js"

echo "开始下载静态资源..."

# 下载 Bootstrap CSS
echo "下载 Bootstrap CSS..."
curl -L -o "$STATIC_DIR/css/bootstrap.min.css" \
  "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"

# 下载 Bootstrap JS
echo "下载 Bootstrap JS..."
curl -L -o "$STATIC_DIR/js/bootstrap.bundle.min.js" \
  "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"

# 下载 Chart.js
echo "下载 Chart.js..."
curl -L -o "$STATIC_DIR/js/chart.umd.min.js" \
  "https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"

echo "✅ 所有资源下载完成！"
echo "文件位置："
echo "  - $STATIC_DIR/css/bootstrap.min.css"
echo "  - $STATIC_DIR/js/bootstrap.bundle.min.js"
echo "  - $STATIC_DIR/js/chart.umd.min.js"

