# LocalWhisper

A blazing-fast, fully local voice-to-text assistant for Windows. Speak naturally, get polished text instantly typed into any application.

**100% offline. No cloud. No subscription. Your voice stays on your machine.**

## Features

- **State-of-the-art transcription** with Whisper large-v3-turbo (6x faster than large-v3)
- **Smart grammar correction** via local LLM (Ollama)
- **Voice Activity Detection** - automatically detects when you stop speaking
- **Instant text injection** - types directly into any focused window
- **5 overlay themes** - Matrix Rain, Dot, Sauron Eye, HUD Ring, Cyborg
- **100+ tunable settings** - customize everything
- **Optimized for speed** - <1 second total latency on modern hardware
- **Multilingual** - handles English, French, and seamless code-switching

## Requirements

### Hardware
- **GPU**: NVIDIA GPU with 6GB+ VRAM (tested on RTX 4090)
- **CPU**: Any modern multi-core CPU
- **OS**: Windows 10/11

### Software
- Python 3.10+
- [Ollama](https://ollama.com/) (for grammar correction)
- CUDA Toolkit (for GPU acceleration)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/localwhisper.git
cd localwhisper
```

### 2. Create a virtual environment

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Download models

```bash
python setup_models.py
```

This downloads:
- Whisper large-v3-turbo (~1.5GB)
- Silero VAD (included)

### 5. Install Ollama and pull a grammar model

```bash
# Install Ollama from https://ollama.com/
ollama pull gemma3:1b
```

## Usage

### Quick Start

```bash
# Windows
run.bat

# Or directly
python main.py
```

### Basic Workflow

1. **Focus** any text field (Notepad, browser, Discord, terminal, etc.)
2. **Press** `Ctrl + Alt + W` (default hotkey)
3. **Speak** naturally - the overlay turns red while listening
4. **Stop** speaking - the overlay turns blue while processing
5. **Done** - your transcribed and corrected text appears

### Overlay Controls

- **Right-click** the overlay to access the menu
- **Unlock Position** to drag it anywhere on screen
- **Settings** to configure everything
- **Quit** to close the app

## Configuration

### Quick Settings (config.py)

```python
HOTKEY = "ctrl+alt+w"          # Trigger key
WHISPER_MODEL_SIZE = "large-v3-turbo"
OLLAMA_MODEL = "gemma3:1b"     # Grammar model
USE_INTELLIGENCE = True         # Enable/disable grammar correction
```

### Full Settings UI

Right-click the overlay and select **Settings** to access:

- **Input Device** - Select your microphone
- **Sensitivity** - Adjust voice detection threshold
- **Push to Talk** - Enable PTT mode with custom key
- **Grammar AI** - Toggle Ollama correction on/off
- **Language Lock** - Force English or French detection
- **Overlay Theme** - Choose from 5 visual styles
- **Injection Mode** - Type vs paste behavior

## Overlay Themes

| Theme | Description |
|-------|-------------|
| **Matrix** | Animated Katakana rain with color-coded states |
| **Dot** | Minimalist pulsing orb |
| **Sauron** | Fiery eye visualization |
| **HUD** | Sci-fi ring interface |
| **Cyborg** | Terminator-style skull |

## Performance

Tested on RTX 4090 + i9-14900K:

| Metric | Value |
|--------|-------|
| Total latency | <1 second |
| Whisper inference | 0.2-0.4s |
| Grammar correction | ~100ms |
| Idle CPU usage | <10% |
| VRAM usage | ~6GB |

## Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| No audio detected | Check Settings > Input Device, ensure mic levels show green |
| Text not appearing | Run as Administrator for terminal injection |
| Slow transcription | Ensure CUDA is properly installed |
| Grammar model missing | Run `ollama pull gemma3:1b` |
| Ollama not starting | App auto-starts Ollama, but you can run `ollama serve` manually |

### Logs

Check `logs/session.log` for detailed error messages.

## Project Structure

```
localwhisper/
├── main.py              # Entry point
├── config.py            # Basic configuration
├── core/
│   ├── audio.py         # Mic capture + VAD
│   ├── transcriber.py   # Whisper inference
│   ├── intelligence.py  # Ollama grammar
│   ├── injector.py      # Text injection
│   └── settings.py      # Settings manager
├── ui/
│   ├── overlay.py       # PyQt6 overlay
│   └── settings_dialog.py
└── tui/
    └── app.py           # Terminal UI alternative
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Transcription | [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) (large-v3-turbo) |
| VAD | [Silero VAD](https://github.com/snakers4/silero-vad) v4 |
| Grammar | [Ollama](https://ollama.com/) + Gemma 3 |
| GUI | PyQt6 |
| Audio | sounddevice (PortAudio) |

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- OpenAI for Whisper
- SYSTRAN for Faster-Whisper
- Silero Team for VAD
- Google for Gemma
- Ollama team for local LLM serving

---

*Built with AI assistance. Runs without it.*
