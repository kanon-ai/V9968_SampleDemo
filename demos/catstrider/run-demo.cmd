@echo off
setlocal
if not defined OPENMSX_EXE set "OPENMSX_EXE=C:\Program Files\openMSX\openmsx.exe"
if not exist "%OPENMSX_EXE%" (
  echo V9968-enabled openMSX was not found. Set OPENMSX_EXE to openmsx.exe.
  exit /b 1
)
if not exist "%~dp0outputs\CATSTRIDER-V9968-legacy-openmsx-internal.rom" (
  echo CATSTRIDER ROM was not found. Run newbuild.cmd first.
  exit /b 1
)
set "CATSTRIDER_RUN=%~dp0work\preview"
if not exist "%CATSTRIDER_RUN%\home" mkdir "%CATSTRIDER_RUN%\home"
if not defined OPENMSX_SYSTEM_DATA for %%I in ("%OPENMSX_EXE%") do set "OPENMSX_SYSTEM_DATA=%%~dpIshare"
if not defined OPENMSX_USER_DATA set "OPENMSX_USER_DATA=%USERPROFILE%\Documents\openMSX\share"
set "OPENMSX_HOME=%CATSTRIDER_RUN%\home"
cd /d "%CATSTRIDER_RUN%"
start "" "%OPENMSX_EXE%" -machine Panasonic_FS-A1ST_V9968 -cart "%~dp0outputs\CATSTRIDER-V9968-legacy-openmsx-internal.rom" -romtype ASCII8
exit /b
