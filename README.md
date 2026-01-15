# LocalWhisper

A blazing-fast, fully local voice-to-text assistant for Windows. Speak naturally, get polished text instantly typed into any application.

**100% offline. No cloud. No subscription. Your voice stays on your machine.**

## Origin Story

This project was built in **45 minutes** by [Antigravity](https://github.com/YOUR_USERNAME) and **Gemini 3.0 Pro** as a proof of concept. The core pipeline (hotkey → record → transcribe → inject) was functional from the start.

After the initial build, additional features were added over time with help from various AI coding assistants:
- Audio visualizer with real-time waveform display
- 5 overlay themes (Matrix Rain, Sauron Eye, etc.)
- MMCSS Pro Audio thread priority for low-latency capture
- P-core affinity optimization for Intel hybrid CPUs
- 100+ tunable settings with live preview

The entire codebase has been optimized for a specific machine (RTX 4090 + i9-14900K). **Your mileage may vary** on different hardware - see the [Hardware Compatibility](#hardware-compatibility) section below.

## Features

- **State-of-the-art transcription** with Whisper large-v3-turbo (6x faster than large-v3)
- **Smart grammar correction** via local LLM (Ollama)
- **Voice Activity Detection** - automatically detects when you stop speaking
- **Instant text injection** - types directly into any focused window
- **5 overlay themes** - Matrix Rain, Dot, Sauron Eye, HUD Ring, Cyborg
- **100+ tunable settings** - customize everything
- **Optimized for speed** - <1 second total latency on RTX 4090
- **Multilingual** - handles English, French, and seamless code-switching (Franglais!)

## Requirements

### Hardware

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU | NVIDIA with 6GB VRAM | RTX 3080+ / RTX 4070+ |
| CPU | Any modern quad-core | Intel 12th gen+ / AMD Ryzen 5000+ |
| RAM | 8GB | 16GB+ |
| OS | Windows 10 | Windows 11 |

### Software

- Python 3.10 or higher
- NVIDIA GPU drivers (CUDA support)
- [Ollama](https://ollama.com/) (optional, for grammar correction)

## Installation

### Quick Install (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/localwhisper.git
cd localwhisper

# 2. Run the installer
install.bat
```

The installer will:
- Create a Python virtual environment
- Install all dependencies
- Download the Whisper model (~1.5GB)
- Check for Ollama and pull the grammar model

### Manual Install

<details>
<summary>Click to expand manual installation steps</summary>

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/localwhisper.git
cd localwhisper

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download models
python setup_models.py

# 5. (Optional) Install Ollama for grammar correction
# Download from https://ollama.com/
ollama pull gemma3:1b
```

</details>

## Usage

### Quick Start

```bash
run.bat
```

### Basic Workflow

1. **Focus** any text field (Notepad, browser, Discord, terminal, etc.)
2. **Press** `Ctrl + Alt + W` (default hotkey)
3. **Speak** naturally - the overlay turns **red** while listening
4. **Stop** speaking - the overlay turns **blue** while processing
5. **Done** - your transcribed text appears in the focused window

### Overlay Controls

| Action | How |
|--------|-----|
| Open menu | Right-click the overlay |
| Move overlay | Menu → Unlock Position → Drag |
| Change settings | Menu → Settings |
| Quit | Menu → Quit |

## Configuration

### Quick Settings

Edit `config.py` to change defaults:

```python
HOTKEY = "ctrl+alt+w"              # Trigger key combination
WHISPER_MODEL_SIZE = "large-v3-turbo"  # Or "medium", "small" for less VRAM
OLLAMA_MODEL = "gemma3:1b"         # Grammar correction model
USE_INTELLIGENCE = True            # Set False to disable grammar correction
```

### Settings UI

Right-click the overlay → **Settings** to access:

- **Input Device** - Select your microphone
- **Sensitivity** - Adjust voice detection threshold (watch the green bar!)
- **Push to Talk** - Enable PTT mode with custom key
- **Grammar AI** - Toggle Ollama correction on/off
- **Language Lock** - Force English or French detection
- **Overlay Theme** - Choose your visual style
- **Injection Mode** - Type vs paste behavior

## Hardware Compatibility

> **Important:** This project was built and optimized for a specific machine (RTX 4090 + i9-14900K with hybrid P-core/E-core architecture). Some optimizations may not work or may need adjustment on your hardware.

### NVIDIA GPUs

Should work out of the box. If you have less VRAM, try a smaller model:

```python
# In config.py
WHISPER_MODEL_SIZE = "medium"  # ~5GB VRAM instead of ~6GB
# or
WHISPER_MODEL_SIZE = "small"   # ~2GB VRAM
```

### AMD GPUs

**Not tested.** Whisper relies on CUDA, which is NVIDIA-only. AMD users would need:
- ROCm support (Linux only, experimental on Windows)
- Or CPU-only mode (much slower)

### AMD CPUs

Should work, but the P-core affinity optimization (`core/cpu_affinity.py`) is Intel-specific. On AMD, you may want to disable it or adjust the core selection logic.

### Tuning for Your Machine

**Pro tip:** Ask your local AI assistant (Claude, GPT, etc.) to help you tune the settings for your specific hardware. Share your specs and the contents of `config.py` and `core/settings.py`, and ask for optimization suggestions.

## Overlay Themes

| Theme | Description |
|-------|-------------|
| **Matrix** | Animated Katakana rain with Knight Rider sweep effect |
| **Dot** | Minimalist pulsing orb |
| **Sauron** | Fiery eye of Mordor |
| **HUD** | Sci-fi holographic ring |
| **Cyborg** | Terminator-style skull |

## Performance

Benchmarked on RTX 4090 + i9-14900K:

| Metric | Value |
|--------|-------|
| Total latency | < 1 second |
| Whisper inference | 0.2 - 0.4s |
| Grammar correction | ~100ms |
| Idle CPU usage | < 10% |
| VRAM usage | ~6GB |

*Results will vary based on your hardware.*

## Troubleshooting

| Problem | Solution |
|---------|----------|
| No audio detected | Settings → Input Device, check the green level bar |
| Text not appearing | Run as Administrator (needed for some apps) |
| Slow transcription | Ensure NVIDIA drivers + CUDA are installed |
| "No module named X" | Run `install.bat` again or `pip install -r requirements.txt` |
| Ollama errors | Run `ollama serve` manually, or disable grammar in config |
| High CPU when idle | Update to latest version (fixed with 10ms sleep in VAD loop) |

### Logs

Detailed logs are saved to `logs/session.log`.

## Project Structure

```
localwhisper/
├── main.py              # Entry point
├── config.py            # Basic configuration
├── install.bat          # One-click installer
├── run.bat              # Start the app
├── core/
│   ├── audio.py         # Mic capture + Silero VAD
│   ├── transcriber.py   # Faster-Whisper inference
│   ├── intelligence.py  # Ollama grammar correction
│   ├── injector.py      # Text injection (type/paste)
│   ├── settings.py      # 100+ tunable parameters
│   ├── cpu_affinity.py  # Intel P-core optimization
│   └── mmcss.py         # Windows Pro Audio priority
├── ui/
│   ├── overlay.py       # PyQt6 overlay (5 themes)
│   └── settings_dialog.py
└── tui/
    └── app.py           # Terminal UI alternative
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Transcription | [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) large-v3-turbo |
| Voice Detection | [Silero VAD](https://github.com/snakers4/silero-vad) v4 (ONNX) |
| Grammar | [Ollama](https://ollama.com/) + Gemma 3 1B |
| GUI | PyQt6 |
| Audio | sounddevice (PortAudio backend) |

## Contributing

Contributions are welcome! This project was AI-assisted from the start, so feel free to use AI tools to help with your PRs.

Some ideas for contributions:
- AMD GPU support (ROCm)
- Linux/macOS ports
- Additional overlay themes
- Smaller/faster model options
- Better language detection

## For AI Assistants

> This section contains structured instructions for AI coding assistants (Claude, GPT, Gemini, etc.) helping users install and configure LocalWhisper.

<details>
<summary>Click to expand AI Assistant Instructions</summary>

### Pre-Installation Checklist

Before starting, verify the user's system meets requirements:

```yaml
requirements:
  os: Windows 10 or 11
  python: ">=3.10"
  gpu: NVIDIA with CUDA support (recommended)
  vram_minimum: 2GB (small model), 5GB (medium), 6GB (large-v3-turbo)
  ram_minimum: 8GB
  disk_space: ~5GB (models + dependencies)

software_dependencies:
  required:
    - Python 3.10+
    - NVIDIA GPU drivers
  optional:
    - Ollama (for grammar correction)
```

### Installation Steps

Execute these steps in order:

```yaml
step_1_clone:
  command: "git clone https://github.com/YOUR_USERNAME/localwhisper.git && cd localwhisper"
  verify: "Directory contains main.py, config.py, requirements.txt"

step_2_create_venv:
  command: "python -m venv venv"
  verify: "venv/Scripts/activate.bat exists"

step_3_activate_venv:
  command: "venv\\Scripts\\activate"  # Windows
  verify: "Command prompt shows (venv) prefix"

step_4_install_dependencies:
  command: "pip install -r requirements.txt"
  verify: "No errors, PyQt6 and faster_whisper installed"
  troubleshooting:
    - error: "CUDA not found"
      solution: "Install NVIDIA CUDA Toolkit or use CPU mode"
    - error: "Microsoft Visual C++ required"
      solution: "Install Visual Studio Build Tools"

step_5_download_models:
  command: "python setup_models.py"
  verify: "silero_vad.onnx exists, models/ directory populated"
  note: "First run downloads ~1.5GB for large-v3-turbo"

step_6_ollama_optional:
  check: "where ollama"
  if_missing: "Direct user to https://ollama.com/download"
  if_present: "ollama pull gemma3:1b"
```

### Hardware-Based Configuration

Adjust `config.py` based on user's hardware:

```yaml
model_selection:
  vram_24gb_plus:  # RTX 4090, 3090
    WHISPER_MODEL_SIZE: "large-v3-turbo"
    COMPUTE_TYPE: "float16"
  vram_8_to_16gb:  # RTX 4070, 3080
    WHISPER_MODEL_SIZE: "large-v3-turbo"
    COMPUTE_TYPE: "float16"
  vram_6_to_8gb:   # RTX 3060, 4060
    WHISPER_MODEL_SIZE: "medium"
    COMPUTE_TYPE: "float16"
  vram_under_6gb:  # GTX 1660, etc.
    WHISPER_MODEL_SIZE: "small"
    COMPUTE_TYPE: "int8"
  no_nvidia_gpu:
    WHISPER_MODEL_SIZE: "small"
    DEVICE: "cpu"
    note: "Will be significantly slower"

cpu_optimization:
  intel_12th_gen_plus:  # Hybrid architecture
    - "P-core affinity enabled by default"
    - "MMCSS Pro Audio registration active"
  amd_ryzen:
    - "May need to disable cpu_affinity.py"
    - "Edit core/cpu_affinity.py or set ENABLE_CPU_AFFINITY=False"
```

### Verification Commands

After installation, verify everything works:

```bash
# Check Python environment
python -c "import faster_whisper; print('Whisper OK')"
python -c "import PyQt6; print('PyQt6 OK')"
python -c "import sounddevice; print(sounddevice.query_devices())"

# Check Ollama (if installed)
ollama list  # Should show gemma3:1b

# Test run (will show overlay)
python main.py
```

### Common Issues & Solutions

```yaml
issue_cuda_not_available:
  symptoms: "Slow transcription, CPU at 100%"
  diagnosis: "python -c \"import torch; print(torch.cuda.is_available())\""
  solutions:
    - "Install NVIDIA CUDA Toolkit 11.8+"
    - "Update NVIDIA drivers"
    - "Reinstall PyTorch with CUDA: pip install torch --index-url https://download.pytorch.org/whl/cu118"

issue_no_audio_input:
  symptoms: "Red overlay but no transcription"
  diagnosis: "Check Settings > Input Device"
  solutions:
    - "Select correct microphone in Settings UI"
    - "Adjust VAD sensitivity threshold"
    - "Check Windows microphone permissions"

issue_text_not_injecting:
  symptoms: "Transcription works but text doesn't appear"
  diagnosis: "Check if target app requires admin"
  solutions:
    - "Run LocalWhisper as Administrator"
    - "Try different injection mode in Settings"

issue_ollama_connection:
  symptoms: "Grammar correction fails"
  diagnosis: "curl http://localhost:11434/api/tags"
  solutions:
    - "Start Ollama: ollama serve"
    - "Pull model: ollama pull gemma3:1b"
    - "Or disable: set USE_INTELLIGENCE=False in config.py"
```

### User Preferences to Ask

When helping a user, gather this information:

```yaml
questions:
  - "What NVIDIA GPU do you have? (or AMD/Intel)"
  - "How much RAM does your system have?"
  - "Do you want grammar correction? (requires Ollama)"
  - "What language(s) will you primarily speak? (English/French/both)"
  - "Do you prefer minimal UI or visual feedback?"
```

### Post-Installation Tips

Share these with the user after successful installation:

```yaml
tips:
  - hotkey: "Default is Ctrl+Alt+W, changeable in config.py"
  - overlay: "Right-click for menu, drag to reposition"
  - settings: "100+ options available in Settings dialog"
  - logs: "Check logs/session.log for debugging"
  - performance: "First transcription is slower (model loading)"
```

</details>

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- **Gemini 3.0 Pro** - Built the initial version in 45 minutes
- **Claude** - Helped polish and add features
- OpenAI for Whisper
- SYSTRAN for Faster-Whisper
- Silero Team for VAD
- Google for Gemma
- Ollama team for local LLM serving

---

*Built with AI. Runs without it.*
