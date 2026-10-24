@echo off
setlocal

cd /d "%~dp0"

echo === MotorAI build ===
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    echo Install it from https://www.python.org/downloads/ ^(tick "Add python.exe to PATH" in the installer^),
    echo then run this script again.
    pause
    exit /b 1
)

if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 goto :error
)

call .venv\Scripts\activate.bat

echo Installing dependencies ^(first run only takes a few minutes^)...
python -m pip install -q --upgrade pip
if errorlevel 1 goto :error
pip install -q -r requirements.txt pyinstaller
if errorlevel 1 goto :error

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo Building MotorAICalibrate.exe ^(one-time check that telemetry reads correctly^)...
pyinstaller --noconfirm --clean --name MotorAICalibrate --console --paths . motorai\capture\verify_capture.py
if errorlevel 1 goto :error

echo.
echo Building MotorAIRecord.exe ^(records a live session while you drive^)...
pyinstaller --noconfirm --clean --name MotorAIRecord --console --paths . motorai\capture\run_session.py
if errorlevel 1 goto :error

echo.
echo Building MotorAI.exe ^(session viewer^)...
pyinstaller --noconfirm --clean --name MotorAI --windowed --collect-all PySide6 --paths . motorai\ui\app.py
if errorlevel 1 goto :error

echo.
echo Building MotorAIReport.exe ^(exports a session as a shareable HTML file^)...
pyinstaller --noconfirm --clean --name MotorAIReport --console --paths . motorai\report\__main__.py
if errorlevel 1 goto :error

echo.
echo === Done ===
echo   dist\MotorAICalibrate\MotorAICalibrate.exe   - run once with AC on track, check it against the HUD
echo   dist\MotorAIRecord\MotorAIRecord.exe          - run this while driving in AC, Ctrl+C to stop
echo   dist\MotorAI\MotorAI.exe                      - double-click to view/compare sessions
echo   dist\MotorAIReport\MotorAIReport.exe          - exports a session to a standalone .html report
echo.
echo Tip: make Desktop shortcuts to these .exe files so you never need to
echo touch this build script or Python again.
pause
exit /b 0

:error
echo.
echo [FAILED] See the error above.
pause
exit /b 1
