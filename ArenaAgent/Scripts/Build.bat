@echo off
rem Builds the ArenaAgent plugin against your launcher-installed UE5.
rem Usage:
rem   Scripts\Build.bat
rem   Scripts\Build.bat -EnginePath "C:\Program Files\Epic Games\UE_5.8"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0BuildPlugin.ps1" %*
exit /b %ERRORLEVEL%
