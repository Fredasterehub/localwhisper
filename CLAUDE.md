# LocalWhisper

A local voice-to-text assistant for Windows that captures speech, transcribes it using Whisper, optionally refines grammar with a local LLM, and injects the text into the active window.

Originally created by Antigravity (Gemini).

## Project Philosophy

- **Leverage open-source** - Use battle-tested libraries and models. Don't reinvent the wheel.
- **No over-engineering** - Keep it simple. Only add complexity when genuinely needed.
- **Robust and elegant** - Write clean, maintainable code that handles edge cases gracefully.

## Agent Usage (IMPORTANT)

To minimize token usage and keep conversations efficient:

1. **Use sub-agents liberally** - Spawn Task agents for exploration, research, and multi-step operations
2. **Use Explore agent** for codebase questions instead of manual Grep/Glob
3. **Use Context7 MCP** for up-to-date library documentation before implementing
4. **Batch parallel operations** - Launch multiple independent agents in a single message
5. **Keep main context lean** - Delegate deep dives to sub-agents, summarize results back

## Git Etiquette (MANDATORY)

The user is new to git. **Every agent must follow proper git practices:**

1. **Commit often** - Small, logical commits with clear messages
2. **Descriptive commit messages** - Use conventional commits format:
   - `feat:` new feature
   - `fix:` bug fix
   - `perf:` performance improvement
   - `refactor:` code restructuring
   - `docs:` documentation only
   - `chore:` maintenance tasks
3. **Always verify before committing** - Run `git status` and `git diff` first
4. **Never force push** - Protect the commit history
5. **Create safety commits** - Before risky changes, commit working state first
6. **Explain git operations** - Help the user understand what's happening
7. **Use .gitignore properly** - Don't commit generated files, caches, or secrets

## Hardware

| Component | Spec |
|-----------|------|
| GPU | NVIDIA RTX 4090 (24GB VRAM) |
| CPU | Intel i9-14900K (8 P-cores + 16 E-cores) |
| OS | Windows 11 |

The i9-14900K has hybrid architecture - audio threads should be pinned to P-cores and registered with MMCSS "Pro Audio" for real-time priority.

## Language

The user speaks **Franglais** - mixed French and English in the same sentence. Transcription and grammar correction must handle seamless code-switching without forcing translation to a single language.

Examples:
- "Hey, tu peux check le fichier config?"
- "J'ai fix le bug dans main.py, it works now"
- "On va deploy ça tomorrow morning"

## Architecture

```
main.py                 # Entry point, hotkey handling, pipeline orchestration
config.py               # Basic config (sample rate, model, hotkeys)

core/
  audio.py              # Mic capture + Silero VAD (voice activity detection)
  transcriber.py        # Faster-Whisper transcription + language detection
  intelligence.py       # Ollama grammar correction
  injector.py           # Text injection (typing vs clipboard-paste)
  settings.py           # 100+ tunable parameters, JSON persistence
  logger.py             # Logging utility

ui/
  overlay.py            # PyQt6 overlay (5 skins: Matrix, Dot, Sauron, HUD, Cyborg)
  settings_dialog.py    # Settings UI with live mic metering

tui/
  app.py                # Terminal UI alternative
  matrix.py             # Matrix animation for TUI
```

## Current Stack (January 2026)

| Component | Model | Notes |
|-----------|-------|-------|
| Transcription | **Whisper large-v3-turbo** | 6x faster than large-v3, same quality |
| VAD | Silero VAD v4 | ONNX Runtime on CPU |
| Grammar | **Gemma 3 1B** via Ollama | Fast, excellent multilingual |
| GUI | PyQt6 | |
| Audio | sounddevice | PortAudio backend |

## Optimizations Implemented

### Quick Wins (Done)
- [x] Whisper large-v3-turbo (6x faster, ~0.2-0.4s inference)
- [x] Gemma 3 1B for grammar (~100ms inference)
- [x] 10ms sleep during silence detection (reduces idle CPU from 70% to <10%)

### Medium Effort (Done)
- [x] MMCSS "Pro Audio" registration for audio threads (`core/mmcss.py`)
- [x] P-core affinity on i9-14900K hybrid CPU (`core/cpu_affinity.py`)

### Backlog
- [ ] Upgrade Silero VAD to v5 (API changed, needs migration)

### Not Doing (Intentionally)
- NeMo/Parakeet (complex Windows setup, WSL2 required)
- Custom T5 grammar pipelines (Ollama is simpler)
- Streaming ASR (segment-based is robust enough)
- Speculative decoding (overkill for single-user)

## Expected Performance

| Metric | Before | After |
|--------|--------|-------|
| Total Latency | ~3s | <1s |
| Whisper inference | 1-2s | 0.2-0.4s |
| Grammar (Ollama) | 0.5-1s | ~0.1s |
| Idle CPU | ~70% | <10% |
| VRAM usage | ~10GB | ~6GB |

## Key Files

| File | Purpose |
|------|---------|
| `config.py` | Model selection, hotkeys, basic settings |
| `core/settings.py` | Full settings manager with 100+ params |
| `user_settings.json` | Persisted user preferences (gitignored) |
| `core/audio.py` | VAD logic, mic capture, noise floor tracking |
| `core/transcriber.py` | Whisper inference, language detection |

## Running

```bash
# Activate venv and run
python main.py

# Or use the batch file
run.bat
```

## Model Recommendations

### STT (Speech-to-Text)
| Model | Speed | Quality | Notes |
|-------|-------|---------|-------|
| **large-v3-turbo** | 6x faster | Same as large-v3 | Current choice |
| Parakeet TDT 0.6B v3 | 20x faster | Slightly lower | Needs NeMo/WSL2 |

### Grammar (via Ollama)
| Model | Command | Speed | Quality |
|-------|---------|-------|---------|
| **Gemma 3 1B** | `ollama pull gemma3:1b` | <100ms | Good |
| Gemma 3 4B | `ollama pull gemma3` | ~200ms | Excellent |
| Qwen 3 4B | `ollama pull qwen3:4b` | ~200ms | Excellent |

## Sources

- [Whisper large-v3-turbo](https://huggingface.co/openai/whisper-large-v3-turbo)
- [Gemma 3 on Ollama](https://ollama.com/library/gemma3)
- [Qwen 3 on Ollama](https://ollama.com/library/qwen3)
- [NVIDIA Parakeet TDT 0.6B v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3)
- [NeMo Toolkit](https://github.com/NVIDIA-NeMo/NeMo)
