@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

:: ===========================================================================
:: Sysadmin Zork launcher
::
:: Menu 0 ("First-time setup") bridges the gap the prologue can't cover on its
:: own: it installs VirtualBox (winget, with a download-page fallback), fetches
:: a Rocky Linux minimal ISO if one isn't already sitting next to this file,
:: and creates + boots the `sysadmin-zork` VM to the spec sheet (2 CPU /
:: 2048 MB / 20 GB EFI disk, NAT + Host-Only NICs). You still install the OS by
:: hand in the VM window -- that's the prologue's job (menu 3) -- but everything
:: up to "installer is on screen" is automated here.
:: ===========================================================================

:: ---- shared config: keep these in lockstep with the engine/spec sheet ------
set "VM_NAME=sysadmin-zork"
set "VM_CPUS=2"
set "VM_RAM_MB=2048"
set "VM_VRAM_MB=128"
set "VM_DISK_MB=20480"
set "HOSTONLY_NET=192.168.56.0"
set "ISO_DIR=%~dp0iso"
:: Rocky Linux 9 minimal (x86_64). Override by dropping any *.iso in .\iso\.
set "ISO_URL=https://download.rockylinux.org/pub/rocky/10.2/isos/x86_64/Rocky-10.2-x86_64-minimal.iso"
set "ISO_NAME=Rocky-10.2-x86_64-minimal.iso"

:: ---- locate a Python runner --------------------------------------------- #
:: Prefer the project venv's interpreter DIRECTLY. Calling .venv\Scripts\python
:: avoids `uv run`'s interpreter-discovery step, which can fail with
:: "Access is denied (os error 5)" on machines where the Windows Store Python
:: App Execution Alias shadows PATH. Fall back to `uv run python` only if no
:: venv exists yet.
set "RUNNER="
if exist ".venv\Scripts\python.exe" (
    set "RUNNER=.venv\Scripts\python.exe"
) else (
    where uv >nul 2>nul
    if %ERRORLEVEL%==0 (
        set "RUNNER=uv run python"
    ) else (
        echo ERROR: no local .venv found and `uv` is not installed.
        echo Create the environment with a real Python 3.12 interpreter:
        echo     uv python find 3.12          ^(copy the path it prints^)
        echo     "PATH_FROM_ABOVE" -m venv .venv
        echo     .venv\Scripts\python.exe -m ensurepip --upgrade
        echo     .venv\Scripts\python.exe -m pip install -e ".[dev]"
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
echo     0  First-time setup         (install VirtualBox + build the VM)
echo.
echo     1  Play on the REAL VM      (the VM must be running -- use 5)
echo     2  Play in FAKE sandbox     (no VM needed; great for a quick try)
echo     3  Run the PROLOGUE         (guided OS install + handshake)
echo     4  Run the SPIKE self-check (proves VM/SSH/snapshot loop, fake)
echo     5  Boot the VM
echo     6  Shut down the VM
echo     Q  Quit
echo.
set "choice="
set /p "choice=Choose [0-6, Q]: "
if "%choice%"=="" goto :menu
if /i "%choice%"=="Q" goto :end
if "%choice%"=="0" call :firsttime & pause & goto :menu
if "%choice%"=="1" %RUNNER% -m engine play & pause & goto :menu
if "%choice%"=="2" %RUNNER% -m engine play --fake & pause & goto :menu
if "%choice%"=="3" %RUNNER% -m engine prologue & pause & goto :menu
if "%choice%"=="4" %RUNNER% -m engine spike --fake & pause & goto :menu
if "%choice%"=="5" call :vm startvm "%VM_NAME%" --type headless & pause & goto :menu
if "%choice%"=="6" call :vm controlvm "%VM_NAME%" acpipowerbutton & pause & goto :menu
goto :menu

:: ===========================================================================
:: First-time setup: VirtualBox -> ISO -> create/configure/boot VM
:: ===========================================================================
:firsttime
echo.
echo   ---- First-time setup -------------------------------------
echo.
call :ensure_vbox
if errorlevel 1 goto :ft_abort
call :ensure_iso
if errorlevel 1 goto :ft_abort
call :ensure_hostonly
call :ensure_vm
if errorlevel 1 goto :ft_abort
echo.
echo   Setup done. The VM window should be opening on the Anaconda installer.
echo   Now run option 3 (PROLOGUE): it walks you through the OS install and
echo   then performs the SSH handshake. GREERSON's spec sheet, in short:
echo       user 'student', check "Make this user administrator",
echo       Minimal Install, then:  sudo systemctl enable --now sshd
echo.
goto :eof
:ft_abort
echo.
echo   Setup did not finish. Fix the issue noted above and run option 0 again.
echo.
goto :eof

:: ---- VirtualBox: detect, else winget install, else download page ----------
:ensure_vbox
call :find_vbm
if defined VBM (
    echo   [VirtualBox] found: !VBM!
    exit /b 0
)
echo   [VirtualBox] not found. Trying winget...
where winget >nul 2>nul
if %ERRORLEVEL%==0 (
    winget install --id Oracle.VirtualBox -e --accept-source-agreements --accept-package-agreements
    call :find_vbm
    if defined VBM (
        echo   [VirtualBox] installed: !VBM!
        exit /b 0
    )
    echo   [VirtualBox] winget ran but VBoxManage still not found.
) else (
    echo   [VirtualBox] winget is not available on this machine.
)
echo.
echo   Install VirtualBox by hand, then re-run option 0:
echo       https://www.virtualbox.org/wiki/Downloads
start "" "https://www.virtualbox.org/wiki/Downloads"
exit /b 1

:: ---- ISO: use any .iso in .\iso\, else download the Rocky minimal ISO ------
:ensure_iso
if not exist "%ISO_DIR%" mkdir "%ISO_DIR%"
set "ISO_PATH="
for %%F in ("%ISO_DIR%\*.iso") do set "ISO_PATH=%%F"
if defined ISO_PATH (
    echo   [ISO] using: !ISO_PATH!
    exit /b 0
)
echo   [ISO] none found in "%ISO_DIR%".
echo   [ISO] downloading Rocky Linux 9 minimal (~2 GB, this takes a while)...
where curl >nul 2>nul
if %ERRORLEVEL%==0 (
    curl -L --fail -o "%ISO_DIR%\%ISO_NAME%" "%ISO_URL%"
) else (
    powershell -NoProfile -Command ^
        "try { Invoke-WebRequest -Uri '%ISO_URL%' -OutFile '%ISO_DIR%\%ISO_NAME%' -UseBasicParsing } catch { exit 1 }"
)
if not exist "%ISO_DIR%\%ISO_NAME%" (
    echo   [ISO] download failed. Grab a Rocky or Alma *minimal* ISO manually,
    echo         drop it in "%ISO_DIR%", and re-run option 0:
    echo             https://rockylinux.org/download
    start "" "https://rockylinux.org/download"
    exit /b 1
)
set "ISO_PATH=%ISO_DIR%\%ISO_NAME%"
echo   [ISO] downloaded: !ISO_PATH!
exit /b 0

:: ---- Host-Only network: ensure a 192.168.56.x adapter exists ---------------
:ensure_hostonly
call :find_vbm
call :get_hoif
if defined HOIF (
    echo   [network] host-only adapter present: !HOIF!
    exit /b 0
)
echo   [network] creating a host-only adapter (192.168.56.1/24)...
"%VBM%" hostonlyif create >nul 2>nul
call :get_hoif
if defined HOIF (
    "%VBM%" hostonlyif ipconfig "!HOIF!" --ip 192.168.56.1 --netmask 255.255.255.0 >nul 2>nul
    echo   [network] host-only adapter ready: !HOIF!
) else (
    echo   [network] WARNING: could not confirm a host-only adapter. The engine
    echo             reaches the VM over 192.168.56.x; if the handshake can't
    echo             connect, add a Host-Only adapter in VirtualBox and retry.
)
exit /b 0

:: ---- helper: set HOIF to the name of the first host-only adapter -----------
:get_hoif
set "HOIF="
set "_HOIF_TMP=%TEMP%\zork_hoif.txt"
"%VBM%" list hostonlyifs > "%_HOIF_TMP%" 2>nul
for /f "tokens=1,* delims=:" %%A in ('findstr /b /i "Name:" "%_HOIF_TMP%"') do (
    if not defined HOIF (
        set "HOIF=%%B"
    )
)
del "%_HOIF_TMP%" >nul 2>nul
if defined HOIF (
    :: trim the single leading space left by the "Name:" split
    set "HOIF=!HOIF:~1!"
)
goto :eof

:: ---- VM: create + configure + attach ISO + boot ----------------------------
:ensure_vm
call :find_vbm
"%VBM%" showvminfo "%VM_NAME%" >nul 2>nul
if %ERRORLEVEL%==0 (
    echo   [vm] "%VM_NAME%" already exists; not recreating.
    echo   [vm] booting it so you can continue the install...
    "%VBM%" showvminfo "%VM_NAME%" --machinereadable | find /i "VMState=""running""" >nul 2>nul
    if errorlevel 1 "%VBM%" startvm "%VM_NAME%" --type gui
    exit /b 0
)

echo   [vm] creating "%VM_NAME%"...
"%VBM%" createvm --name "%VM_NAME%" --ostype RedHat_64 --register || exit /b 1

echo   [vm] applying spec (%VM_CPUS% CPU, %VM_RAM_MB% MB RAM, EFI, NAT + Host-Only)...
"%VBM%" modifyvm "%VM_NAME%" --cpus %VM_CPUS% --memory %VM_RAM_MB% --vram 16 --firmware efi
"%VBM%" modifyvm "%VM_NAME%" --graphicscontroller vmsvga --vram %VM_VRAM_MB%
"%VBM%" modifyvm "%VM_NAME%" --nic1 nat
"%VBM%" modifyvm "%VM_NAME%" --nic2 hostonly
:: bind NIC2 to the first host-only adapter by name
call :get_hoif
if defined HOIF (
    "%VBM%" modifyvm "%VM_NAME%" --hostonlyadapter2 "!HOIF!"
)

echo   [vm] creating a %VM_DISK_MB% MB dynamic disk...
set "VDI=%~dp0%VM_NAME%.vdi"
"%VBM%" createmedium disk --filename "%VDI%" --size %VM_DISK_MB% --format VDI >nul || exit /b 1
"%VBM%" storagectl "%VM_NAME%" --name "SATA" --add sata --controller IntelAhci --portcount 2
"%VBM%" storageattach "%VM_NAME%" --storagectl "SATA" --port 0 --device 0 --type hdd --medium "%VDI%"

echo   [vm] attaching installer ISO...
"%VBM%" storageattach "%VM_NAME%" --storagectl "SATA" --port 1 --device 0 --type dvddrive --medium "!ISO_PATH!"
"%VBM%" modifyvm "%VM_NAME%" --boot1 dvd --boot2 disk --boot3 none --boot4 none

echo   [vm] booting into the installer...
"%VBM%" startvm "%VM_NAME%" --type gui || exit /b 1
exit /b 0

:: ---- helper: locate VBoxManage.exe, set VBM (empty if not found) -----------
:find_vbm
set "VBM="
if exist "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe" set "VBM=C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
if not defined VBM if exist "C:\Program Files (x86)\Oracle\VirtualBox\VBoxManage.exe" set "VBM=C:\Program Files (x86)\Oracle\VirtualBox\VBoxManage.exe"
if not defined VBM (
    where VBoxManage.exe >nul 2>nul && set "VBM=VBoxManage.exe"
)
goto :eof

:: ---- helper: run a VBoxManage command (used by menu 5/6) -------------------
:vm
call :find_vbm
if not defined VBM (
    echo VBoxManage not found. Run option 0 first.
    goto :eof
)
"%VBM%" %*
goto :eof

:end
endlocal