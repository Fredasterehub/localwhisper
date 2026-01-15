@echo off
setlocal enabledelayedexpansion
title LocalWhisper Installer
color 0B
cls

echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║                                                              ║
echo  ║   ██╗      ██████╗  ██████╗ █████╗ ██╗                       ║
echo  ║   ██║     ██╔═══██╗██╔════╝██╔══██╗██║                       ║
echo  ║   ██║     ██║   ██║██║     ███████║██║                       ║
echo  ║   ██║     ██║   ██║██║     ██╔══██║██║                       ║
echo  ║   ███████╗╚██████╔╝╚██████╗██║  ██║███████╗                  ║
echo  ║   ╚══════╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝╚══════╝                  ║
echo  ║                                                              ║
echo  ║   ██╗    ██╗██╗  ██╗██╗███████╗██████╗ ███████╗██████╗       ║
echo  ║   ██║    ██║██║  ██║██║██╔════╝██╔══██╗██╔════╝██╔══██╗      ║
echo  ║   ██║ █╗ ██║███████║██║███████╗██████╔╝█████╗  ██████╔╝      ║
echo  ║   ██║███╗██║██╔══██║██║╚════██║██╔═══╝ ██╔══╝  ██╔══██╗      ║
echo  ║   ╚███╔███╔╝██║  ██║██║███████║██║     ███████╗██║  ██║      ║
echo  ║    ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝╚══════╝╚═╝     ╚══════╝╚═╝  ╚═╝      ║
echo  ║                                                              ║
echo  ║            100%% Local Voice-to-Text Assistant               ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.
echo  Press any key to start the installation wizard...
pause >nul

:: ============================================
:: STEP 1: Check Python
:: ============================================
cls
echo.
echo  ┌──────────────────────────────────────────────────────────────┐
echo  │  STEP 1/5: Checking Python Installation                      │
echo  └──────────────────────────────────────────────────────────────┘
echo.

python --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo  [ERROR] Python not found!
    echo.
    echo  Please install Python 3.10 or higher from:
    echo  https://www.python.org/downloads/
    echo.
    echo  IMPORTANT: Check "Add Python to PATH" during installation!
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo  [OK] Python %PYVER% detected
echo.
timeout /t 2 >nul

:: ============================================
:: STEP 2: Hardware Detection
:: ============================================
cls
echo.
echo  ┌──────────────────────────────────────────────────────────────┐
echo  │  STEP 2/5: Detecting Hardware                                │
echo  └──────────────────────────────────────────────────────────────┘
echo.
echo  Scanning your system...
echo.

:: Detect GPU
set GPU_NAME=Unknown
set GPU_VRAM=0
set HAS_NVIDIA=0

for /f "tokens=*" %%i in ('wmic path win32_videocontroller get name 2^>nul ^| findstr /i "NVIDIA"') do (
    set GPU_NAME=%%i
    set HAS_NVIDIA=1
)

if %HAS_NVIDIA%==1 (
    echo  [GPU] !GPU_NAME!

    :: Try to get VRAM (approximate from name)
    echo !GPU_NAME! | findstr /i "4090" >nul && set GPU_VRAM=24
    echo !GPU_NAME! | findstr /i "4080" >nul && set GPU_VRAM=16
    echo !GPU_NAME! | findstr /i "4070" >nul && set GPU_VRAM=12
    echo !GPU_NAME! | findstr /i "3090" >nul && set GPU_VRAM=24
    echo !GPU_NAME! | findstr /i "3080" >nul && set GPU_VRAM=10
    echo !GPU_NAME! | findstr /i "3070" >nul && set GPU_VRAM=8
    echo !GPU_NAME! | findstr /i "3060" >nul && set GPU_VRAM=12

    if !GPU_VRAM! GTR 0 (
        echo        Estimated VRAM: ~!GPU_VRAM! GB
    )
) else (
    color 0E
    echo  [WARNING] No NVIDIA GPU detected!
    echo  LocalWhisper requires an NVIDIA GPU for fast transcription.
    echo  It may still work on CPU but will be much slower.
    color 0B
)

:: Detect RAM
for /f "tokens=2 delims==" %%i in ('wmic computersystem get TotalPhysicalMemory /value 2^>nul') do (
    set /a RAM_GB=%%i / 1073741824
)
echo  [RAM] !RAM_GB! GB

:: Detect CPU
for /f "tokens=2 delims==" %%i in ('wmic cpu get name /value 2^>nul') do set CPU_NAME=%%i
echo  [CPU] !CPU_NAME!

echo.
timeout /t 3 >nul

:: ============================================
:: STEP 3: Model Selection
:: ============================================
cls
echo.
echo  ┌──────────────────────────────────────────────────────────────┐
echo  │  STEP 3/5: Choose Whisper Model                              │
echo  └──────────────────────────────────────────────────────────────┘
echo.
echo  Based on your hardware, here are your options:
echo.

:: Determine recommendation
set RECOMMENDED=large-v3-turbo
if !GPU_VRAM! LSS 6 set RECOMMENDED=medium
if !GPU_VRAM! LSS 4 set RECOMMENDED=small
if %HAS_NVIDIA%==0 set RECOMMENDED=small

echo  ┌─────────────────────────────────────────────────────────────┐
echo  │  Model          │ VRAM   │ Speed   │ Quality               │
echo  ├─────────────────┼────────┼─────────┼───────────────────────┤
echo  │  1. small       │ ~2 GB  │ Fast    │ Good                  │
echo  │  2. medium      │ ~5 GB  │ Medium  │ Better                │
echo  │  3. large-v3-turbo │ ~6 GB │ Fast │ Best (Recommended)    │
echo  └─────────────────────────────────────────────────────────────┘
echo.
echo  Recommended for your system: %RECOMMENDED%
echo.

set MODEL_CHOICE=3
set /p MODEL_CHOICE="  Select model [1-3, default=3]: "

if "%MODEL_CHOICE%"=="1" (
    set WHISPER_MODEL=small
) else if "%MODEL_CHOICE%"=="2" (
    set WHISPER_MODEL=medium
) else (
    set WHISPER_MODEL=large-v3-turbo
)

echo.
echo  Selected: %WHISPER_MODEL%
timeout /t 2 >nul

:: ============================================
:: STEP 4: Ollama (Grammar Correction)
:: ============================================
cls
echo.
echo  ┌──────────────────────────────────────────────────────────────┐
echo  │  STEP 4/5: Grammar Correction (Optional)                     │
echo  └──────────────────────────────────────────────────────────────┘
echo.
echo  LocalWhisper can use Ollama (local LLM) to polish your text:
echo  - Fix grammar and punctuation
echo  - Clean up "uh", "um", repetitions
echo  - Handle mixed French/English (Franglais)
echo.
echo  This requires installing Ollama (~500MB) and a grammar model (~1GB).
echo.

set INSTALL_OLLAMA=Y
set /p INSTALL_OLLAMA="  Install Ollama for grammar correction? [Y/n]: "

if /i "%INSTALL_OLLAMA%"=="n" (
    set USE_GRAMMAR=0
    echo.
    echo  Skipping Ollama. You can install it later from https://ollama.com
) else (
    set USE_GRAMMAR=1
)

timeout /t 2 >nul

:: ============================================
:: STEP 5: Installation
:: ============================================
cls
echo.
echo  ┌──────────────────────────────────────────────────────────────┐
echo  │  STEP 5/5: Installing                                        │
echo  └──────────────────────────────────────────────────────────────┘
echo.
echo  Configuration Summary:
echo  ----------------------
echo  Whisper Model: %WHISPER_MODEL%
echo  Grammar (Ollama): %USE_GRAMMAR%
echo.
echo  Press any key to begin installation...
pause >nul
echo.

:: Create venv
echo  [1/4] Creating virtual environment...
if not exist "venv" (
    python -m venv venv
    if errorlevel 1 (
        echo  [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
)
echo        Done.

:: Install deps
echo  [2/4] Installing Python dependencies...
echo        This may take a few minutes...
call venv\Scripts\activate.bat
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if errorlevel 1 (
    echo  [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo        Done.

:: Update config with selected model
echo  [3/4] Configuring model: %WHISPER_MODEL%...
powershell -Command "(Get-Content config.py) -replace 'WHISPER_MODEL_SIZE = \".*\"', 'WHISPER_MODEL_SIZE = \"%WHISPER_MODEL%\"' | Set-Content config.py"
echo        Done.

:: Download models
echo  [4/4] Downloading AI models...
echo        Whisper %WHISPER_MODEL% - this may take a while...
python setup_models.py
echo        Done.

:: Ollama
if %USE_GRAMMAR%==1 (
    echo.
    echo  Installing Ollama...
    where ollama >nul 2>&1
    if errorlevel 1 (
        echo.
        echo  Ollama not found. Opening download page...
        echo  Please install Ollama, then run: ollama pull gemma3:1b
        start https://ollama.com/download
        echo.
        echo  After installing Ollama, run this command:
        echo    ollama pull gemma3:1b
    ) else (
        echo  Ollama found. Pulling grammar model...
        ollama pull gemma3:1b
    )
)

:: ============================================
:: COMPLETE
:: ============================================
cls
echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║                                                              ║
echo  ║              INSTALLATION COMPLETE!                          ║
echo  ║                                                              ║
echo  ╠══════════════════════════════════════════════════════════════╣
echo  ║                                                              ║
echo  ║  To start LocalWhisper:                                      ║
echo  ║                                                              ║
echo  ║    Double-click: run.bat                                     ║
echo  ║                                                              ║
echo  ║  Default hotkey: Ctrl + Alt + W                              ║
echo  ║  Right-click overlay for settings                            ║
echo  ║                                                              ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.

if %USE_GRAMMAR%==1 (
    where ollama >nul 2>&1
    if errorlevel 1 (
        color 0E
        echo  [REMINDER] Don't forget to install Ollama and run:
        echo    ollama pull gemma3:1b
        echo.
        color 0B
    )
)

echo  Press any key to exit...
pause >nul
