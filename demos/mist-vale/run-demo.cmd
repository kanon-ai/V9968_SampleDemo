@echo off
setlocal
if not defined OPENMSX_EXE set "OPENMSX_EXE=C:\Program Files\openMSX\openmsx.exe"
if not exist "%~dp0work\emulator" mkdir "%~dp0work\emulator"
cd /d "%~dp0work\emulator"
if not defined OPENMSX_SYSTEM_DATA for %%I in ("%OPENMSX_EXE%") do set "OPENMSX_SYSTEM_DATA=%%~dpIshare"
set "OPENMSX_HOME=./home"
set "OPENMSX_USER_DATA=./user"
start "" "%OPENMSX_EXE%" -machine Panasonic_FS-A1ST_V9968 -cart ../../outputs/MIST_VALE-V9968-legacy-openmsx-internal.rom -romtype ASCII8 -script ../../tools/preview.tcl
