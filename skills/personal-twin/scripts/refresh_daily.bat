@echo off
rem personal-twin 每日增量刷新：重算能力画像 + 刷新注入摘要
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
echo ===== [%date% %time%] daily refresh START ===== >> "%~dp0..\logs\refresh.log"
"C:\Users\Lenovo\AppData\Local\Programs\Python\Python313\python.exe" "%~dp0run_refresh.py" >> "%~dp0..\logs\refresh.log" 2>&1
echo ===== [%date% %time%] daily refresh END ===== >> "%~dp0..\logs\refresh.log"
