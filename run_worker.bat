@echo off
setlocal

for %%I in ("%~dp0.") do set "PULSECHECK_ROOT=%%~fI"
call "%PULSECHECK_ROOT%\scripts\resolve_python.bat"
if errorlevel 1 goto :missing_python

echo Starting PulseCheck worker...
"%PULSECHECK_PYTHON%" "%PULSECHECK_ROOT%\client.py" --config "%PULSECHECK_ROOT%\config\worker.json"
goto :done

:missing_python
echo.
echo No usable Python runtime was found.
echo Run install_pulsecheck.bat first.

:done
echo.
pause
endlocal
