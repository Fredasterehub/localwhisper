<!--
AI ASSISTANTS: For concise installation instructions, see llms.txt in this repository.
URL: https://raw.githubusercontent.com/Fredasterehub/localwhisper/master/llms.txt
-->

# LocalWhisper

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Windows](https://img.shields.io/badge/Windows-Ready-0078D6?logo=windows&logoColor=white)](#installation)
[![macOS](https://img.shields.io/badge/macOS-Ready-000000?logo=apple&logoColor=white)](#macos)
[![NVIDIA CUDA](https://img.shields.io/badge/NVIDIA-CUDA-76B900?logo=nvidia&logoColor=white)](https://developer.nvidia.com/cuda-toolkit)
[![Whisper](https://img.shields.io/badge/OpenAI-Whisper-412991?logo=openai)](https://github.com/openai/whisper)
[![Built with AI](https://img.shields.io/badge/Built%20with-AI%20%F0%9F%A4%96-blueviolet)](#acknowledgments)

> Blazing-fast, fully local voice-to-text for **Windows & macOS**. Speak naturally, get text typed into any application — including terminals.

**100% offline. No cloud. No subscription. Your voice stays on your machine.**

## Why LocalWhisper?

Commercial solutions like Whisper Flow don't work in terminals — only in IDEs. I needed voice-to-text that works *everywhere*: terminals, SSH sessions, browsers, any text field.

Built in 45 minutes by [Antigravity](https://github.com/Fredasterehub) + **Gemini 3.0 Pro**, then polished with **Claude**. 100% vibe-coded. Not enterprise-ready. Use at your own risk — but it works great.

## Features

- **Sub-second latency** — ~0.6s total on RTX 4090
- **Works everywhere** — terminals, IDEs, browsers, Discord, anything
- **Two modes** — Voice Activation (default) or Push-to-Talk
- **Two interfaces** — GUI overlay or Terminal UI (TUI)
- **5 overlay themes** — Matrix Rain, Sauron Eye, HUD Ring, Dot, Cyborg
- **Grammar correction** — optional local LLM via Ollama
- **Multilingual** — English, French, and Franglais code-switching

## Quick Start

### Windows

```bash
git clone https://github.com/Fredasterehub/localwhisper.git
cd localwhisper
install.bat
run.bat
```

### macOS

Native Apple Silicon version ready — upload coming very soon. Watch this repo.

## Usage

1. **Focus** any text field
2. **Press** `Ctrl + Alt + W`
3. **Speak** — overlay turns red
4. **Stop** — overlay turns blue, text appears

Right-click overlay for settings. Edit `config.py` for hotkey, model size, etc.

## Performance

Benchmarked on RTX 4090 + i9-14900K:

| Metric | Value |
|--------|-------|
| **Total latency** | **~0.6s** |
| Whisper inference | ~0.23s |
| Grammar correction | ~0.35s |
| VRAM usage | ~6GB |

Run `python benchmark_interactive.py` to test your hardware.

## Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU | NVIDIA 6GB VRAM | RTX 3080+ |
| RAM | 8GB | 16GB+ |
| OS | Windows 10 / macOS 12+ | Windows 11 / macOS 14+ |

**Software:** Python 3.10+, NVIDIA drivers, [Ollama](https://ollama.com/) (optional)

<details>
<summary><strong>Hardware Compatibility Notes</strong></summary>

### NVIDIA GPUs
Works out of the box. Less VRAM? Use smaller model:
```python
WHISPER_MODEL_SIZE = "medium"  # 5GB VRAM
WHISPER_MODEL_SIZE = "small"   # 2GB VRAM
```

### AMD GPUs
Not tested. Needs ROCm (Linux) or CPU mode (slow).

### AMD CPUs
Works, but P-core affinity optimization is Intel-specific. May need adjustment.

### Apple Silicon
Native Metal acceleration. No Rosetta needed.

</details>

## Tech Stack

| Component | Technology |
|-----------|------------|
| Transcription | [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) large-v3-turbo |
| VAD | [Silero VAD](https://github.com/snakers4/silero-vad) v4 |
| Grammar | [Ollama](https://ollama.com/) + Gemma 3 1B |
| GUI | PyQt6 |
| TUI | [Textual](https://textual.textualize.io/) |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| No audio | Settings → Input Device, check green level bar |
| Text not appearing | Run as Administrator |
| Slow | Check NVIDIA drivers + CUDA installed |
| Ollama errors | Run `ollama serve` or disable in config |

Logs: `logs/session.log`

<details>
<summary><strong>For AI Assistants</strong></summary>

See [`llms.txt`](llms.txt) for concise installation instructions optimized for LLMs.

Raw URL: `https://raw.githubusercontent.com/Fredasterehub/localwhisper/master/llms.txt`

</details>

## Contributing

Contributions welcome! Ideas:
- AMD GPU support (ROCm)
- Linux port
- More overlay themes
- Smaller model options

## License

MIT — see [LICENSE](LICENSE)

## Acknowledgments

- **Antigravity** — Creator
- **Google Gemini 3.0 Pro** — Initial build
- **Claude** — Polish and optimization
- OpenAI (Whisper), SYSTRAN (Faster-Whisper), Silero (VAD), Ollama

---

*"Talk is cheap. Show me the code."* — **Linus Torvalds**
