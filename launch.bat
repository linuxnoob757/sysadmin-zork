@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

:: Sysadmin Zork — desktop launcher menu.
:: Keeps a single entry point that mirrors the noir prologue's
:: "pager's always watching" tone: the menu itself is the NOC dashboard.
title Sysadmin Zork

:: ---- locate a Python runner ------------------------------------------------
set "RUNNER="
if exist ".venv\Scripts\python.exe" (
    set "RUNNER=.venv\Scripts\python.exe"
) else (
    where uv >nul 2>nul
    if !ERRORLEVEL!==0 (
        set "RUNNER=uv run python"
    ) else (
        echo ERROR: no local .venv found and `uv` is not installed.
        echo Create the environment first:  uv sync
        pause
        goto :eof
    )
)

:menu
cls
echo.
echo   ============================================================
echo      SYSADMIN ZORK  --  NOC dashboard
echo   ============================================================
echo.
echo     1  Play (fake sandbox)     no VM needed; quick session
echo     2  Play (real VM)          the VM must be running
echo     3  Spike self-check        proves engine+loader+sandbox
echo     4  First-time setup        VirtualBox + ISO + VM (winget)
echo     5  Boot the VM (headless)  
echo     6  Shut down the VM
echo     Q  Quit
echo.
set "choice="
set /p "choice=Choose [1-6, Q]: "
if "%choice%"=="" goto :menu
if /i "%choice%"=="Q" goto :end
if "%choice%"=="1" %RUNNER% -m engine play --fake & pause & goto :menu
if "%choice%"=="2" %RUNNER% -m engine play & pause & goto :menu
if "%choice%"=="3" %RUNNER% -m engine spike --fake & pause & goto :menu
if "%choice%"=="4" call :firsttime & pause & goto :menu
if "%choice%"=="5" call :vm startvm "sysadmin-zork" --type headless & pause & goto :menu
if "%choice%"=="6" call :vm controlvm "sysadmin-zork" acpipowerbutton & pause & goto :menu
goto :menu

:firsttime
echo.
echo   ---- First-time setup -------------------------------------
echo   Installing VirtualBox via winget, fetching Rocky Linux 9, and
echo   building the sysadmin-zork VM (2 CPU / 2048 MB / 20 GB EFI).
echo   The installer window will appear; run option 3 (prologue) after
echo   installing the OS by hand.
call :ensure_vbox
if errorlevel 1 goto :ft_abort
call :ensure_iso
if errorlevel 1 goto :ft_abort
call :ensure_hostonly
call :ensure_vm
if errorlevel 1 goto :ft_abort
echo   Setup complete. Boot the VM (option 5), install the OS, then
echo   run option 3 (prologue) to finish the handshake.
goto :eof
:ft_abort
echo   Setup did not finish — fix the issue above and re-run option 4.
goto :eof

:ensure_vbox
set "VBM="
if exist "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe" set "VBM=C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
if not defined VBM if exist "C:\Program Files (x86)\Oracle\VirtualBox\VBoxManage.exe" set "VBM=C:\Program Files (x86)\Oracle\VirtualBox\VBoxManage.exe"
if not defined VBM where VBoxManage.exe >nul 2>nul && set "VBM=VBoxManage.exe"
if defined VBM exit /b 0
where winget >nul 2>nul && winget install --id Oracle.VirtualBox -e --accept-source-agreements --accept-package-agreements
call :find_vbm
if defined VBM exit /b 0
echo   VirtualBox not found. winget may not be available. Install by hand:
echo       https://www.virtualbox.org/wiki/Downloads
start "" "https://www.virtualbox.org/wiki/Downloads"
exit /b 1

:find_vbm
set "VBM="
if exist "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe" set "VBM=C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
if not defined VBM if exist "C:\Program Files (x86)\Oracle\VirtualBox\VBoxManage.exe" set "VBM=C:\Program Files (x86)\Oracle\VirtualBox\VBoxManage.exe"
if not defined VBM where VBoxManage.exe >nul 2>nul && set "VBM=VBoxManage.exe"
goto :eof

:ensure_iso
set "ISO_DIR=%~dp0iso"
if not exist "%ISO_DIR%" mkdir "%ISO_DIR%"
set "ISO_PATH="
for %%F in ("%ISO_DIR%\*.iso") do set "ISO_PATH=%%F"
if defined ISO_PATH exit /b 0
echo   No ISO found in iso\ — downloading Rocky Linux 9 minimal.
where curl >nul 2>nul && (
    curl -L --fail -o "%ISO_DIR%\Rocky-9-minimal.iso" "https://download.rockylinux.org/pub/rocky/9/isos/x86_64/Rocky-9-x86_64-minimal.iso"
) || (
    powershell -NoProfile -Command "try { Invoke-WebRequest -Uri 'https://download.rockylinux.org/pub/rocky/9/isos/x86_64/Rocky-9-x86_64-minimal.iso' -OutFile '%ISO_DIR%\Rocky-9-minimal.iso' -UseBasicParsing } catch { exit 1 }"
)
exit /b 0

:ensure_hostonly
call :find_vbm
if not defined VBM exit /b 0
"%VBM%" hostonlyif create >nul 2>nul
exit /b 0

:ensure_vm
call :find_vbm
"%VBM%" showvminfo "sysadmin-zork" >nul 2>nul && exit /b 0
set "VDI=%~dp0sysadmin-zork.vdi"
"%VBM%" createvm --name "sysadmin-zork" --ostype RedHat_64 --register
"%VBM%" modifyvm "sysadmin-zork" --cpus 2 --memory 2048 --vram 128 --firmware efi --nic1 nat --nic2 hostonly --graphicscontroller vmsvga
"%VBM%" createmedium disk --filename "%VDI%" --size 20480 --format VDI >nul
"%VBM%" storagectl "sysadmin-zork" --name "SATA" --add sata --controller IntelAhci --portcount 2
"%VBM%" storageattach "sysadmin-zork" --storagectl "SATA" --port 0 --device 0 --type hdd --medium "%VDI%"
"%VBM%" storageattach "sysadmin-zork" --storagectl "SATA" --port 1 --device 0 --type dvddrive --medium "!ISO_PATH!"
exit /b 0

:vm
call :find_vbm
if not defined VBM echo VBoxManage not found. Run option 4 first. & goto :eof
"%VBM%" %*
goto :eof

:end
endlocal
