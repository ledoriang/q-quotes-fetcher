@echo off
rem Double-clickable fallback if .vbs is blocked by policy.
rem The cmd window closes quickly; the PowerShell GUI window appears after.
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0show-quotes.ps1"