@echo off
chcp 65001 > nul
echo ========================================================
echo   CosmoStars Casino - Telegram Bot ^& Mini App
echo ========================================================
echo.
cd /d "%~dp0"
python main.py
pause
