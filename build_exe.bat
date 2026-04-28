@echo off
setlocal

for %%I in ("%~dp0.") do set "PULSECHECK_ROOT=%%~fI"
call "%PULSECHECK_ROOT%\scripts\resolve_python.bat"
if errorlevel 1 goto :missing_python

echo Ensuring PyInstaller is installed...
"%PULSECHECK_PYTHON%" -m pip install pyinstaller
if errorlevel 1 goto :build_failed

echo Building manager executable...
"%PULSECHECK_PYTHON%" -m PyInstaller --onefile --name PulseCheckManager "%PULSECHECK_ROOT%\server.py"
if errorlevel 1 goto :build_failed

echo Building worker executable...
"%PULSECHECK_PYTHON%" -m PyInstaller --onefile --name PulseCheckWorker "%PULSECHECK_ROOT%\client.py"
if errorlevel 1 goto :build_failed

if not exist "%PULSECHECK_ROOT%\dist\config" mkdir "%PULSECHECK_ROOT%\dist\config"
if not exist "%PULSECHECK_ROOT%\dist\tasks" mkdir "%PULSECHECK_ROOT%\dist\tasks"
copy /Y "%PULSECHECK_ROOT%\config\manager.json" "%PULSECHECK_ROOT%\dist\config\manager.json" >nul
copy /Y "%PULSECHECK_ROOT%\config\worker.json" "%PULSECHECK_ROOT%\dist\config\worker.json" >nul
copy /Y "%PULSECHECK_ROOT%\tasks\tasks.txt" "%PULSECHECK_ROOT%\dist\tasks\tasks.txt" >nul

echo.
echo Build complete.
echo Check the dist folder for PulseCheckManager.exe, PulseCheckWorker.exe, config, and tasks.
goto :done

:missing_python
echo.
echo No usable Python runtime was found.
echo Run install_pulsecheck.bat first.
goto :done

:build_failed
echo.
echo Failed to build the executables.
echo Make sure install_pulsecheck.bat completed successfully first.

:done
echo.
pause
endlocal
