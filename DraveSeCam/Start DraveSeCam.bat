@echo off
setlocal enabledelayedexpansion
title DraveSeCam

rem --- Een Python zoeken: keten 3.13 - 3.10, anders python ---
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
    echo Geen Python gevonden. Installeer Python 3.10 t/m 3.13 van python.org.
    echo.
    pause
    exit /b 1
)

rem --- Kernpakketten (beeld) controleren / installeren ---
!PY! -c "import PyQt6, cv2, numpy" >nul 2>&1
if errorlevel 1 (
    echo Eenmalig de benodigde pakketten installeren ^(PyQt6, opencv-python, numpy^)...
    echo Dit kan even duren.
    echo.
    !PY! -m pip install --upgrade PyQt6 opencv-python numpy
)

rem --- Geluid-pakketten (optioneel) - mislukken stopt de app niet ---
!PY! -c "import sounddevice, imageio_ffmpeg" >nul 2>&1
if errorlevel 1 (
    echo Geluid-pakketten installeren ^(optioneel: microfoon + samenvoegen^)...
    echo.
    !PY! -m pip install --upgrade sounddevice imageio-ffmpeg
)

!PY! DraveSeCam.py
endlocal
