@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

:: Locate a Python runner: prefer `uv`, fall back to a local project venv.
set "RUNNER="
where uv >nul 2>nul
if %ERRORLEVEL%==0 (
    set "RUNNER=uv run python"
) else (
    if exist ".venv\Scripts\python.exe" (
        set "RUNNER=.venv\Scripts\python"
    ) else (
        echo ERROR: neither `uv` nor a local .venv was found.
        echo Install uv from https://docs.astral.sh/uv/ , or create the venv with:
        echo     uv venv
        echo     uv pip install -e ".[dev]"
        pause
        goto :eof
    )
)

title Sysadmin Zork
goto :menu

:menu
cls
echo.
echo   ============================================================
echo      SYSADMIN ZORK  --  launcher
echo   ============================================================
echo.
echo     1  Play on the REAL VM      (the VM must be running -- use 5)
echo     2  Play in FAKE sandbox     (no VM needed; great for a quick try)
echo     3  Run the PROLOGUE         (first-time VM install + setup)
echo     4  Run the SPIKE self-check  (proves VM/SSH/snapshot loop, fake)
echo     5  Boot the VM
echo     6  Shut down the VM
echo     Q  Quit
echo.
set "choice="
set /p "choice=Choose [1-6, Q]: "
if "%choice%"=="" goto :menu
if /i "%choice%"=="Q" goto :end
if "%choice%"=="1" %RUNNER% -m engine play
if "%choice%"=="2" %RUNNER% -m engine play --fake
if "%choice%"=="3" %RUNNER% -m engine prologue
if "%choice%"=="4" %RUNNER% -m engine spike --fake
if "%choice%"=="5" call :vm startvm sysadmin-zork --type headless
if "%choice%"=="6" call :vm controlvm sysadmin-zork acpipowerbutton
goto :menu

:: Helper: run a VBoxManage command, auto-detecting its location.
:vm
set "VBM=C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
if not exist "%VBM%" set "VBM=VBoxManage.exe"
"%VBM%" %*
goto :eof

:end
endlocal
