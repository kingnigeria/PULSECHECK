@echo off
setlocal

for %%I in ("%~dp0.") do set "PULSECHECK_ROOT=%%~fI"
set "BOOTSTRAP_PYTHON="

if exist "%PULSECHECK_ROOT%\.venv\Scripts\python.exe" (
    set "BOOTSTRAP_PYTHON=%PULSECHECK_ROOT%\.venv\Scripts\python.exe"
) else (
    for /f "delims=" %%I in ('where python 2^>nul') do (
        if not defined BOOTSTRAP_PYTHON set "BOOTSTRAP_PYTHON=%%I"
    )
    for /f "delims=" %%I in ('where py 2^>nul') do (
        if not defined BOOTSTRAP_PYTHON set "BOOTSTRAP_PYTHON=%%I"
    )
    if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
        if not defined BOOTSTRAP_PYTHON set "BOOTSTRAP_PYTHON=%LocalAppData%\Programs\Python\Python312\python.exe"
    )
    if not defined BOOTSTRAP_PYTHON if exist "%ProgramFiles%\Python312\python.exe" (
        set "BOOTSTRAP_PYTHON=%ProgramFiles%\Python312\python.exe"
    )
    if not defined BOOTSTRAP_PYTHON if exist "C:\Users\harus\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
        set "BOOTSTRAP_PYTHON=C:\Users\harus\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    )
)

if not defined BOOTSTRAP_PYTHON goto :missing_python

echo %BOOTSTRAP_PYTHON% | find /I "codex-runtimes" >nul
if not errorlevel 1 goto :runtime_only

echo [1/3] Creating virtual environment...
"%BOOTSTRAP_PYTHON%" -m venv "%PULSECHECK_ROOT%\.venv" --system-site-packages
if errorlevel 1 goto :venv_fallback

echo [2/3] Upgrading pip...
"%PULSECHECK_ROOT%\.venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :pip_failed

echo [3/3] Installing requirements...
"%PULSECHECK_ROOT%\.venv\Scripts\python.exe" -m pip install -r "%PULSECHECK_ROOT%\requirements.txt"
if errorlevel 1 goto :pip_failed

echo.
echo PulseCheck setup completed.
echo Use run_manager.bat on the manager machine.
echo Use run_worker.bat on each worker machine.
goto :done

:runtime_only
echo Detected the bundled local runtime.
"%BOOTSTRAP_PYTHON%" -c "import psutil, cryptography; print('runtime_ok')"
if errorlevel 1 goto :venv_failed
echo.
echo PulseCheck is ready to run with the detected local runtime.
echo Use run_manager.bat on the manager machine.
echo Use run_worker.bat on each worker machine.
goto :done

:missing_python
echo.
echo Python was not found.
echo Install Python 3.12+ and check "Add Python to PATH", then run this file again.
goto :done

:venv_fallback
echo.
echo Virtual environment creation failed. Trying runtime fallback...
if exist "%PULSECHECK_ROOT%\.venv" rmdir /s /q "%PULSECHECK_ROOT%\.venv"
"%BOOTSTRAP_PYTHON%" -c "import psutil, cryptography; print('runtime_ok')"
if errorlevel 1 goto :venv_failed
echo.
echo PulseCheck can still run with the detected Python runtime on this machine.
echo The launch scripts will use that runtime automatically.
goto :done

:venv_failed
echo.
echo Failed to create a virtual environment, and the fallback runtime is missing dependencies.
echo Install Python 3.12+ and run this file again on the target machine.
goto :done

:pip_failed
echo.
echo Failed while installing dependencies.
echo If you are offline, connect to the internet and run install_pulsecheck.bat again.

:done
echo.
pause
endlocal
