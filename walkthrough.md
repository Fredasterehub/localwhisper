# Local Whisper Flow - Walkthrough

## Overview
You have successfully built a local, SOTA voice assistant clone that runs on your Windows 11 machine (4090/i9).
It listens for a hotkey, records your voice, transcribes it using the best available model (`faster-whisper large-v3`), fixes grammar/accents using `Ollama`, and types the result into your active window.

## How to Run
1.  Navigate to `D:\DEV\localwhisper`
2.  **First Time Only**: Run `venv\Scripts\python setup_models.py` to download the models (Wait for it to finish).
3.  Double-click **`run.bat`** to start the app.
4.  A small gray dot will appear in the bottom-right corner of your screen.

## How to Use
1.  **Focus**: Click on a text field (Notepad, Discord, Browser, Terminal, etc.) where you want the text to appear.
2.  **Hotkey**: Press **`Ctrl + Alt + W`** (Changeable in `config.py`)
3.  **Speak**: Speak your command. The Matrix Rain turns **RED** (Listening).
4.  **Wait**: Stop speaking. The Matrix Rain turns **BLUE** (Processing).
5.  **Result**: The corrected text will be typed into your active window.

## Customizing the Overlay & Settings
-   **Hybrid Injection**: Types short text for effect, but **Instantly Pastes** long text to prevent terminal crashes and improve speed.
-   **Audio Visualizer**: See live microphone input levels in the Settings panel. the first run to help you setup your mic.
-   **Move It**: Right-click -> **Unlock Position**. Drag it to a new spot.
-   **Settings Menu**: Right-click -> **Settings**. (Note: The voice engine pauses while settings are open).
    -   **Input Device**: Select Mic and see the **GREEN BAR** move when you talk.
    -   **Sensitivity**: Adjust slider. Set it so the bar only moves when you speak.
    -   **Push to Talk**: Enable PTT and bind your key.
    -   **Enable AI Grammar**: Toggle the Mistral/Llama AI on/off instantly. Uncheck for "Raw Mode" (faster), Check for "Grammar Mode" (cleaner).
    -   **VAD Threshold**: Adjust sensitivity (Green Bar > Slider = Recording).
-   **Lock It**: Right-click -> **Lock Position**.
-   **Quit**: Right-click -> **Quit**.

## Configuration
Edit `config.py` to change:
-   `HOTKEY`: Your preferred keybind.
-   `OLLAMA_MODEL`: `llama3` by default. Ensure you have run `ollama pull llama3`.
-   `WHISPER_MODEL_SIZE`: `large-v3` (Best) or `medium.en` (Faster).
-   `USE_INTELLIGENCE`: Set to `False` for **Raw Mode** (Pure Dictation). Set to `True` for **Grammar Mode** (AI Correction).

## Features
-   **Voice Activity Detection**: Automatically detecting when you stop speaking.
-   **Grammar Flow**: Uses LLM to fix "broken English" or "Frenglish".
-   **Overlay**: Minimalist status indicator.
-   **GPU Acceleration**: Runs fully on your RTX 4090.

## Troubleshooting
-   **Logs**: Check `logs/session.log` for detailed error messages.
-   **Startup Crash "atexit"?** Fixed in v2.
-   **Brief Red Dot/No record?** Open **Settings** and lower the **Sensitivity**.
-   **"Access Denied"**: Ignore this warning.
-   **"DLL Not Found"**: Fixed in v5 using dynamic path loading.
-   **Ollama**: The app now auto-starts `ollama serve` if it's not running.
-   **Terminal Crash**: If typing causes issues, the app now automatically switches to **Paste Mode** for long text.
-   **Language Lock**: In Settings, force **French** or **English** if the app keeps incorrectly translating your words.
-   **Matrix Rain**: Click and drag to move. Right-click to Lock/Quit. It uses authentic Katakana glyphs.
-   **Typing in Terminals?** The app now auto-requests Administrator privileges. Click "Yes" on the UAC prompt.
