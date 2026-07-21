@echo off
chcp 65001 >nul
title 📊 開啟大樂透 Dashboard

cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 找不到 Python
    pause
    exit /b
)

echo 📊 正在產生分析 Dashboard...
python main.py --analyze
