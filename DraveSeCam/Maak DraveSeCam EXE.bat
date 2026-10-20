@echo off
setlocal enabledelayedexpansion
title Maak DraveSeCam EXE

echo ============================================
echo   DraveSeCam - EXE bouwen (Dravenlock)
echo ============================================
echo.

set "PY="
for %%V in (3.13 3.12 3.11 3.10) do (
    if not defined PY (
        py -%%V -c "import sys" >nul 2>&1 && set "PY=py -%%V"
    )
)
if not defined PY (
    python -c "import sys" >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo Geen geschikte Python gevonden ^(3.10 t/m 3.13^).
    echo Installeer Python van python.org en probeer opnieuw.
    echo.
    pause
    exit /b 1
)
echo Python gevonden: !PY!
echo.

rem --- Benodigde pakketten controleren / installeren ---
!PY! -c "import PyQt6, cv2, numpy" >nul 2>&1
if errorlevel 1 (
    echo Benodigde pakketten installeren ^(PyQt6, opencv-python, numpy^)...
    !PY! -m pip install --upgrade PyQt6 opencv-python numpy
)
!PY! -c "import sounddevice, imageio_ffmpeg" >nul 2>&1
if errorlevel 1 (
    echo Geluid-pakketten installeren ^(sounddevice, imageio-ffmpeg^)...
    !PY! -m pip install --upgrade sounddevice imageio-ffmpeg
)
!PY! -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo PyInstaller installeren...
    !PY! -m pip install --upgrade pyinstaller
    if errorlevel 1 (
        echo Installeren van PyInstaller is mislukt.
        echo.
        pause
        exit /b 1
    )
)
echo.

echo Bezig met bouwen... dit kan even duren.
echo.
!PY! -m PyInstaller --noconfirm --clean "DraveSeCam.spec"
echo.

if exist "dist\DraveSeCam.exe" (
    echo ============================================
    echo   KLAAR. De EXE staat hier:
    echo   dist\DraveSeCam.exe
    echo ============================================
) else (
    echo Er ging iets mis: geen EXE gevonden in de map dist.
    echo Lees de meldingen hierboven voor de oorzaak.
)
echo.
pause
endlocal
