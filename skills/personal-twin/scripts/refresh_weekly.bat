@echo off
rem personal-twin 每周全量刷新：重算 + 快照 + 成长轨迹 + 注入摘要
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
echo ===== [%date% %time%] WEEKLY full refresh START ===== >> "%~dp0..\logs\refresh.log"
"C:\Users\Lenovo\AppData\Local\Programs\Python\Python313\python.exe" "%~dp0run_refresh.py" --full >> "%~dp0..\logs\refresh.log" 2>&1
echo ===== [%date% %time%] WEEKLY full refresh END ===== >> "%~dp0..\logs\refresh.log"
