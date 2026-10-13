@echo off
set SCRIPT_DIR=%~dp0
set REPO_ROOT=%SCRIPT_DIR%..
set PYTHONPATH=%REPO_ROOT%;%PYTHONPATH%
python -m agentic %*
exit /b %ERRORLEVEL%
