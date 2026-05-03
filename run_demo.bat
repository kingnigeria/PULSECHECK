@echo off
setlocal
for %%I in ("%~dp0.") do set "PULSECHECK_ROOT=%%~fI"
call "%PULSECHECK_ROOT%\scripts\resolve_python.bat"
if errorlevel 1 goto :missing_python

echo.
echo ============================================================
echo    PulseCheck Demo - Automated Setup and Run
echo ============================================================
echo.
echo Starting demo setup...
echo.

"%PULSECHECK_PYTHON%" "%PULSECHECK_ROOT%\setup_demo.py"
goto :done

:missing_python
echo No usable Python runtime with PulseCheck dependencies was found.
echo Run install_pulsecheck.bat first.

:done
pause
endlocal
