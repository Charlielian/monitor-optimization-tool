#!/bin/bash

# 离线图表修复验证脚本

echo "========================================"
echo "离线图表显示修复验证"
echo "========================================"
echo ""

# 检查 Bootstrap Icons CSS
echo "1. 检查 Bootstrap Icons CSS..."
if [ -f "static/css/bootstrap-icons.min.css" ]; then
    SIZE=$(ls -lh static/css/bootstrap-icons.min.css | awk '{print $5}')
    echo "   ✅ bootstrap-icons.min.css 存在 ($SIZE)"
else
    echo "   ❌ bootstrap-icons.min.css 不存在"
    echo "   执行: python download_bootstrap_icons.py"
fi

echo ""

# 检查字体文件
echo "2. 检查 Bootstrap Icons 字体文件..."
if [ -f "static/fonts/bootstrap-icons.woff" ]; then
    SIZE=$(ls -lh static/fonts/bootstrap-icons.woff | awk '{print $5}')
    echo "   ✅ bootstrap-icons.woff 存在 ($SIZE)"
else
    echo "   ❌ bootstrap-icons.woff 不存在"
fi

if [ -f "static/fonts/bootstrap-icons.woff2" ]; then
    SIZE=$(ls -lh static/fonts/bootstrap-icons.woff2 | awk '{print $5}')
    echo "   ✅ bootstrap-icons.woff2 存在 ($SIZE)"
else
    echo "   ❌ bootstrap-icons.woff2 不存在"
fi

echo ""

# 检查 base.html 是否已修复
echo "3. 检查 base.html 配置..."
if grep -q "url_for('static', filename='css/bootstrap-icons.min.css')" templates/base.html; then
    echo "   ✅ base.html 已配置使用本地 Bootstrap Icons"
else
    echo "   ❌ base.html 未配置本地 Bootstrap Icons"
fi

echo ""

# 检查其他静态资源
echo "4. 检查其他静态资源..."
if [ -f "static/css/bootstrap.min.css" ]; then
    echo "   ✅ Bootstrap CSS 存在"
else
    echo "   ⚠️  Bootstrap CSS 不存在（可能使用CDN）"
fi

if [ -f "static/js/chart.umd.min.js" ]; then
    echo "   ✅ Chart.js 存在"
else
    echo "   ⚠️  Chart.js 不存在（可能使用CDN）"
fi

echo ""
echo "========================================"
echo "验证完成"
echo "========================================"
echo ""

# 统计
TOTAL=0
PASSED=0

if [ -f "static/css/bootstrap-icons.min.css" ]; then
    PASSED=$((PASSED + 1))
fi
TOTAL=$((TOTAL + 1))

if [ -f "static/fonts/bootstrap-icons.woff" ]; then
    PASSED=$((PASSED + 1))
fi
TOTAL=$((TOTAL + 1))

if [ -f "static/fonts/bootstrap-icons.woff2" ]; then
    PASSED=$((PASSED + 1))
fi
TOTAL=$((TOTAL + 1))

if grep -q "url_for('static', filename='css/bootstrap-icons.min.css')" templates/base.html; then
    PASSED=$((PASSED + 1))
fi
TOTAL=$((TOTAL + 1))

echo "检查结果: $PASSED/$TOTAL 项通过"
echo ""

if [ $PASSED -eq $TOTAL ]; then
    echo "✅ 所有检查通过！离线图表显示已修复。"
    echo ""
    echo "建议:"
    echo "  1. 重启应用: python app.py"
    echo "  2. 访问应用并测试图标显示"
    echo "  3. 可以在离线环境下测试"
    exit 0
else
    echo "❌ 部分检查未通过，请执行修复："
    echo ""
    echo "修复步骤:"
    echo "  1. 下载 Bootstrap Icons: python download_bootstrap_icons.py"
    echo "  2. 检查 templates/base.html 配置"
    echo "  3. 重新运行此验证脚本"
    exit 1
fi
