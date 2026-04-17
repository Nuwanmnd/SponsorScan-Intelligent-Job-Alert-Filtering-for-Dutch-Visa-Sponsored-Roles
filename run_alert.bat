
@echo off
cd /d "d:\Projects\GmailAlert"
call venv\Scripts\activate.bat
python main.py
if %errorlevel% neq 0 (
    echo Error occurred.
    pause
)
