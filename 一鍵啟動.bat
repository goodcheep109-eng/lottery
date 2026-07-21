@echo off
chcp 65001 >nul
title 🎰 台灣大樂透分析系統

echo.
echo  ╔══════════════════════════════════════╗
echo  ║   🎰  台灣大樂透智慧分析系統         ║
echo  ║   自動更新資料 + 開啟 Dashboard      ║
echo  ╚══════════════════════════════════════╝
echo.

:: 切換到程式所在目錄
cd /d "%~dp0"

:: 檢查 Python 是否安裝
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 找不到 Python，請先安裝 Python 3.x
    echo    下載網址：https://www.python.org/downloads/
    pause
    exit /b
)

:: 檢查套件是否安裝
echo 🔍 檢查套件...
python -c "import requests, pandas, bs4" >nul 2>&1
if errorlevel 1 (
    echo 📦 正在安裝必要套件...
    pip install -r requirements.txt
    echo.
)

:: 更新資料
echo 🔄 正在更新開獎資料...
echo    （首次執行約需 1~2 分鐘，請稍候）
echo.
python main.py --update
echo.

:: 產生 Dashboard 並開啟瀏覽器
echo 📊 正在產生分析 Dashboard...
python main.py --analyze
echo.

echo ✅ 完成！瀏覽器應已自動開啟。
echo    如果沒有自動開啟，請手動開啟：
echo    %~dp0docs\index.html
echo.
pause
