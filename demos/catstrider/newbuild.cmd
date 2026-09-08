@echo off
setlocal
cd /d "%~dp0"
if defined PYTHON_EXE (
  "%PYTHON_EXE%" tools\build.py
  exit /b
)
where py >nul 2>nul
if not errorlevel 1 (
  py -3 tools\build.py
  exit /b
)
where python >nul 2>nul
if not errorlevel 1 (
  python tools\build.py
  exit /b
)
echo Python was not found. Install Python and Pillow, or set PYTHON_EXE.
echo Set PASMO to pasmo.exe if it is not on PATH or in the default location.
exit /b 1
