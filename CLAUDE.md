# LocalWhisper

Local voice-to-text for **Windows & macOS**. Captures speech, transcribes with Whisper, optional grammar correction via Ollama, injects text anywhere (including terminals).

Created by Antigravity + Gemini 3.0 Pro, polished with Claude.

## Project Philosophy

- **Leverage open-source** - Battle-tested libraries, don't reinvent the wheel
- **No over-engineering** - Simple > complex
- **100% vibe-coded** - Not enterprise-ready, use at your own risk

## User Context

- **Hardware:** RTX 4090 + i9-14900K (hybrid P-core/E-core)
- **Language:** Franglais (mixed French/English in same sentence)
- **Git skill:** Beginner - explain operations, commit often with clear messages

## Architecture

```
main.py                 # Entry point, hotkey handling, pipeline
config.py               # Model, hotkeys, Ollama URL (use 127.0.0.1!)

core/
  audio.py              # Mic capture + Silero VAD
  transcriber.py        # Faster-Whisper inference
  intelligence.py       # Ollama grammar (uses requests.Session!)
  injector.py           # Text injection
  settings.py           # Settings manager

ui/
  overlay.py            # PyQt6 overlay (5 themes)
  settings_dialog.py    # Settings UI

tui/
  app.py                # Terminal UI alternative
```

## Stack

| Component | Tech | Notes |
|-----------|------|-------|
| Transcription | Whisper large-v3-turbo | ~0.23s inference |
| VAD | Silero VAD v4 | ONNX on CPU |
| Grammar | Gemma 3 1B via Ollama | ~0.35s (after optimization) |
| GUI | PyQt6 | 5 overlay themes |
| TUI | Textual | Matrix rain style |

## Performance (Real Benchmarks)

| Metric | Value |
|--------|-------|
| **Total latency** | **~0.6s** |
| Whisper inference | ~0.23s |
| Ollama grammar | ~0.35s |
| VRAM usage | ~6GB |

## Critical Optimizations

These are **mandatory** for good performance on Windows:

1. **Use `127.0.0.1` not `localhost`** in `config.py`
   - Windows DNS lookup for localhost is slow (~2s)

2. **Use `requests.Session()`** in `intelligence.py`
   - Reuses TCP connections, avoids overhead

Without these: ~2.7s latency. With these: ~0.6s.

## Git Rules

1. Commit often with conventional commits (`feat:`, `fix:`, `perf:`, `docs:`)
2. Always `git status` and `git diff` before committing
3. Never force push
4. Explain git operations to user

## Running

```bash
python main.py      # GUI mode
python main_tui.py  # TUI mode
python benchmark_interactive.py  # Test performance
```

## Key Config

```python
# config.py
WHISPER_MODEL_SIZE = "large-v3-turbo"  # or "medium", "small"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"  # NOT localhost!
OLLAMA_MODEL = "gemma3:1b"
USE_INTELLIGENCE = True  # False to disable grammar
HOTKEY = "<ctrl>+<alt>+w"
```
