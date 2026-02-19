@echo off
chcp 65001 >nul
title 干扰小区数据提取工具

echo ========================================
echo   干扰小区数据提取工具 - GUI版本
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.6或更高版本
    echo.
    pause
    exit /b 1
)

echo [信息] Python版本:
python --version
echo.

REM 检查必要文件
if not exist "gui_interference_extractor.py" (
    echo [错误] 找不到 gui_interference_extractor.py 文件
    echo.
    pause
    exit /b 1
)

if not exist "standalone_interference_extractor.py" (
    echo [错误] 找不到 standalone_interference_extractor.py 文件
    echo.
    pause
    exit /b 1
)

echo [信息] 正在启动GUI工具...
echo.

REM 启动GUI程序
python gui_interference_extractor.py

if errorlevel 1 (
    echo.
    echo [错误] 程序运行出错
    echo.
    pause
)
