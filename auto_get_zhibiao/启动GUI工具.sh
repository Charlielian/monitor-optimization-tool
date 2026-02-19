#!/bin/bash

echo "========================================"
echo "  干扰小区数据提取工具 - GUI版本"
echo "========================================"
echo ""

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "[错误] 未检测到Python，请先安装Python 3.6或更高版本"
        echo ""
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

echo "[信息] Python版本:"
$PYTHON_CMD --version
echo ""

# 检查必要文件
if [ ! -f "gui_interference_extractor.py" ]; then
    echo "[错误] 找不到 gui_interference_extractor.py 文件"
    echo ""
    exit 1
fi

if [ ! -f "standalone_interference_extractor.py" ]; then
    echo "[错误] 找不到 standalone_interference_extractor.py 文件"
    echo ""
    exit 1
fi

echo "[信息] 正在启动GUI工具..."
echo ""

# 启动GUI程序
$PYTHON_CMD gui_interference_extractor.py

if [ $? -ne 0 ]; then
    echo ""
    echo "[错误] 程序运行出错"
    echo ""
fi
