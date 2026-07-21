@echo off
chcp 65001 >nul
title 🔄 更新大樂透資料

echo.
echo  ╔══════════════════════════════════════╗
echo  ║   🔄  更新最新開獎資料               ║
echo  ╚══════════════════════════════════════╝
echo.

cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 找不到 Python
    pause
    exit /b
)

echo 🔄 正在從台灣彩券抓取最新資料...
python main.py --update
echo.
echo ✅ 資料更新完成！
echo.
pause
