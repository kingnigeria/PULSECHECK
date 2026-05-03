@echo off
REM Toggle Worker Config - Reversible Configuration Helper
REM Double-click this file to toggle between local and network worker modes

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0toggle_worker_config.ps1"
pause