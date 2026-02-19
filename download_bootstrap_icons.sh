#!/bin/bash
# 下载 Bootstrap Icons 到本地，支持离线环境

echo "================================================"
echo "下载 Bootstrap Icons 到本地"
echo "================================================"

# 创建目录
mkdir -p static/css
mkdir -p static/fonts

# 下载 Bootstrap Icons CSS
echo "正在下载 Bootstrap Icons CSS..."
curl -L -o static/css/bootstrap-icons.min.css \
  https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css

if [ $? -eq 0 ]; then
  echo "✓ Bootstrap Icons CSS 下载成功"
else
  echo "✗ Bootstrap Icons CSS 下载失败"
  exit 1
fi

# 下载字体文件
echo "正在下载 Bootstrap Icons 字体文件..."

# 下载 woff2 格式
curl -L -o static/fonts/bootstrap-icons.woff2 \
  https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/fonts/bootstrap-icons.woff2

if [ $? -eq 0 ]; then
  echo "✓ Bootstrap Icons 字体文件下载成功"
else
  echo "✗ Bootstrap Icons 字体文件下载失败"
  exit 1
fi

# 下载 woff 格式（备用）
curl -L -o static/fonts/bootstrap-icons.woff \
  https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/fonts/bootstrap-icons.woff

# 修改 CSS 文件中的字体路径
echo "正在修改字体路径..."
sed -i.bak 's|../fonts/bootstrap-icons.woff2|/static/fonts/bootstrap-icons.woff2|g' static/css/bootstrap-icons.min.css
sed -i.bak 's|../fonts/bootstrap-icons.woff|/static/fonts/bootstrap-icons.woff|g' static/css/bootstrap-icons.min.css

# 删除备份文件
rm -f static/css/bootstrap-icons.min.css.bak

echo ""
echo "================================================"
echo "✓ Bootstrap Icons 下载完成！"
echo "================================================"
echo "文件位置:"
echo "  - CSS: static/css/bootstrap-icons.min.css"
echo "  - 字体: static/fonts/bootstrap-icons.woff2"
echo "  - 字体: static/fonts/bootstrap-icons.woff"
echo ""
echo "现在可以在离线环境使用 Bootstrap Icons 了！"
