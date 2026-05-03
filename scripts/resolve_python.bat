@echo off

for %%I in ("%~dp0..") do set "PULSECHECK_ROOT=%%~fI"
set "PULSECHECK_PYTHON="

if exist "%PULSECHECK_ROOT%\.venv\Scripts\python.exe" (
    set "PULSECHECK_PYTHON=%PULSECHECK_ROOT%\.venv\Scripts\python.exe"
    call :validate_python
    if not errorlevel 1 exit /b 0
    set "PULSECHECK_PYTHON="
)

if not defined PULSECHECK_PYTHON if exist "C:\Users\harus\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
    set "PULSECHECK_PYTHON=C:\Users\harus\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    call :validate_python
    if errorlevel 1 set "PULSECHECK_PYTHON="
)

if not defined PULSECHECK_PYTHON if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    set "PULSECHECK_PYTHON=%LocalAppData%\Programs\Python\Python312\python.exe"
    call :validate_python
    if errorlevel 1 set "PULSECHECK_PYTHON="
)

if not defined PULSECHECK_PYTHON if exist "%ProgramFiles%\Python312\python.exe" (
    set "PULSECHECK_PYTHON=%ProgramFiles%\Python312\python.exe"
    call :validate_python
    if errorlevel 1 set "PULSECHECK_PYTHON="
)

for /f "delims=" %%I in ('where python 2^>nul') do (
    if not defined PULSECHECK_PYTHON (
        set "PULSECHECK_PYTHON=%%I"
        call :validate_python
        if errorlevel 1 set "PULSECHECK_PYTHON="
    )
)

for /f "delims=" %%I in ('where py 2^>nul') do (
    if not defined PULSECHECK_PYTHON (
        set "PULSECHECK_PYTHON=%%I"
        call :validate_python
        if errorlevel 1 set "PULSECHECK_PYTHON="
    )
)

if not defined PULSECHECK_PYTHON exit /b 1
exit /b 0

:validate_python
"%PULSECHECK_PYTHON%" -c "import sys, psutil, cryptography" >nul 2>&1
exit /b %errorlevel%
