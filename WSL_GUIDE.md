# How to Run LocalWhisper TUI in WSL (Windows Subsystem for Linux)

This guide will help you run the cyberpunk TUI version of LocalWhisper inside your Linux terminal on Windows.

## Prerequisites

- You must have **WSL** custom installed (e.g., Ubuntu).
- You must have **Python 3** installed in WSL (`sudo apt install python3 python3-pip python3-venv`).
- **Ollama** should be running on Windows (it usually works fine from WSL).

## Step-by-Step

### 1. Open WSL
1. Open **Command Prompt** or **PowerShell** (or Windows Terminal).
2. Type `wsl` and press Enter. You should see your prompt change (e.g., `user@computer:~$`).

### 2. Navigate to Your Project
Your Windows drives are "mounted" in `/mnt/`.
- If your project is in `D:\DEV\localwhisper`, type:
  ```bash
  cd /mnt/d/DEV/localwhisper
  ```
- If it's on `C:`, use `/mnt/c/`.

### 3. Create a Linux Setup (One-Time Only)
The Python environment on Windows is separate from WSL. You need to create a new one for Linux.

1. **Create a virtual environment**:
   ```bash
   python3 -m venv venv_wsl
   ```
2. **Activate it**:
   ```bash
   source venv_wsl/bin/activate
   ```
3. **Install Dependencies**:
   ```bash
   # You might need portaudio for sound
   sudo apt-get update && sudo apt-get install portaudio19-dev

   # Install Python libraries
   pip install -r requirements.txt
   ```

### 4. Run the TUI
Make sure your environment is active (you see `(venv_wsl)` at the start of your line).

```bash
python3 main_tui.py
```

## Troubleshooting

### "No Audio Device Found"
Audio in WSL is tricky.
- **WSL 2** generally supports audio out of the box (via PulseAudio compatibility).
- If microphone input fails, you might need to **forward your microphone** to WSL or just run the TUI on Windows PowerShell instead. The TUI looks just as cool in PowerShell!

### Ollama Connection
If the TUI can't find Ollama:
- Ensure Ollama is running on Windows.
- WSL usually can see Windows ports on `localhost`.
