"""
LocalWhisper Interactive Benchmark
Real-world performance test with actual speech.

Run: python benchmark_interactive.py
"""

import sys
import os

# --- CUDA DLL FIX ---
try:
    venv_base = os.path.dirname(os.path.dirname(sys.executable))
    nvidia_base = os.path.join(venv_base, "Lib", "site-packages", "nvidia")
    for root, dirs, files in os.walk(nvidia_base):
        for d in dirs:
            if d == "bin" or d == "lib":
                path = os.path.join(root, d)
                os.environ["PATH"] += os.pathsep + path
except Exception:
    pass
# --------------------

import time
import json
import numpy as np
import sounddevice as sd
import requests
from datetime import datetime

import config
from core.settings import manager as settings

# Results storage
results = []

# Global session for connection reuse (fixes 2s overhead on Windows)
_ollama_session = requests.Session()

def record_audio(duration_hint=None):
    """Record audio until user presses Enter or silence detected."""
    print("\n" + "="*50)
    print("RECORDING - Speak now!")
    print("Press ENTER when done speaking...")
    print("="*50 + "\n")

    sample_rate = config.SAMPLE_RATE
    chunk_duration = 0.1  # 100ms chunks
    chunk_samples = int(sample_rate * chunk_duration)

    audio_chunks = []
    recording = True

    # Start recording in a separate thread
    import threading

    def input_thread():
        nonlocal recording
        input()  # Wait for Enter
        recording = False

    t = threading.Thread(target=input_thread, daemon=True)
    t.start()

    # Record until Enter is pressed
    with sd.InputStream(samplerate=sample_rate, channels=1, dtype='float32') as stream:
        while recording:
            chunk, _ = stream.read(chunk_samples)
            audio_chunks.append(chunk.flatten())

    audio = np.concatenate(audio_chunks)
    duration = len(audio) / sample_rate

    print(f"\nRecorded {duration:.1f} seconds of audio")
    return audio, duration

def transcribe_whisper(model, audio):
    """Transcribe audio with Whisper, return text and timing."""
    start = time.perf_counter()

    segments, info = model.transcribe(
        audio,
        task="transcribe",
        language=None,  # Auto-detect
        beam_size=5,
        vad_filter=False,
    )

    text = " ".join([s.text for s in segments]).strip()
    elapsed = time.perf_counter() - start

    detected_lang = getattr(info, "language", "unknown")

    return text, elapsed, detected_lang

def correct_with_ollama(text):
    """Apply Ollama grammar correction, return corrected text and timing."""
    if not text:
        return text, 0.0

    prompt = (
        "You are a STRICT copy editor for dictated prose.\n"
        "Return ONLY the corrected text. No quotes, no explanations.\n\n"
        "Rules:\n"
        "1) Preserve meaning exactly. Do NOT paraphrase.\n"
        "2) Do NOT translate or change language.\n"
        "3) Fix only: obvious spelling, obvious homophone mistakes, basic punctuation, capitalization.\n"
        "4) Remove only these fillers when standalone words: euh, um, uh, ah, like.\n"
        "5) If unsure, output the input unchanged.\n\n"
        f"Input: {text}\n"
        "Corrected:\n"
    )

    payload = {
        "model": config.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.0},
    }

    start = time.perf_counter()
    try:
        response = _ollama_session.post(config.OLLAMA_URL, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        corrected = (result.get("response", "") or "").strip()

        # Clean up quotes if present
        if corrected.startswith('"') and corrected.endswith('"'):
            corrected = corrected[1:-1]

        elapsed = time.perf_counter() - start
        return corrected if corrected else text, elapsed
    except Exception as e:
        elapsed = time.perf_counter() - start
        print(f"Ollama error: {e}")
        return text, elapsed

def run_test_cycle(model, cycle_num):
    """Run one complete test cycle (with and without Ollama)."""
    print(f"\n{'#'*50}")
    print(f"TEST CYCLE {cycle_num}")
    print(f"{'#'*50}")

    # Record audio
    audio, duration = record_audio()

    if duration < 0.5:
        print("Audio too short, skipping...")
        return None

    # Test 1: Whisper only (no Ollama)
    print("\n--- TEST 1: Whisper ONLY (no grammar correction) ---")
    whisper_text, whisper_time, detected_lang = transcribe_whisper(model, audio)

    print(f"\nLanguage detected: {detected_lang}")
    print(f"Whisper time: {whisper_time:.3f}s")
    print(f"Transcript:\n  \"{whisper_text}\"")

    # Test 2: Whisper + Ollama
    print("\n--- TEST 2: Whisper + Ollama (with grammar correction) ---")

    # Re-transcribe (to be fair, fresh inference)
    whisper_text_2, whisper_time_2, _ = transcribe_whisper(model, audio)
    corrected_text, ollama_time = correct_with_ollama(whisper_text_2)
    total_time_with_ollama = whisper_time_2 + ollama_time

    print(f"\nWhisper time: {whisper_time_2:.3f}s")
    print(f"Ollama time: {ollama_time:.3f}s")
    print(f"Total time: {total_time_with_ollama:.3f}s")
    print(f"Transcript (raw):\n  \"{whisper_text_2}\"")
    print(f"Transcript (corrected):\n  \"{corrected_text}\"")

    # Show comparison
    print("\n" + "="*50)
    print("COMPARISON")
    print("="*50)
    print(f"\nAudio duration: {duration:.1f}s")
    print(f"\n[WITHOUT Ollama] {whisper_time:.3f}s")
    print(f"  \"{whisper_text}\"")
    print(f"\n[WITH Ollama] {total_time_with_ollama:.3f}s (+{ollama_time:.3f}s)")
    print(f"  \"{corrected_text}\"")

    # Automatic quality assessment
    print("\n" + "-"*50)
    print("AUTOMATIC QUALITY ASSESSMENT")
    print("-"*50)

    changes_made = whisper_text.strip() != corrected_text.strip()
    if changes_made:
        print("Ollama made changes: YES")
        # Simple diff
        if len(corrected_text) > len(whisper_text) * 1.5:
            print("Warning: Ollama output is much longer (possible hallucination)")
        elif len(corrected_text) < len(whisper_text) * 0.5:
            print("Warning: Ollama output is much shorter (possible truncation)")
        else:
            print("Change size: Reasonable")
    else:
        print("Ollama made changes: NO (text identical)")

    # Store result
    result = {
        "cycle": cycle_num,
        "timestamp": datetime.now().isoformat(),
        "audio_duration_s": round(duration, 2),
        "detected_language": detected_lang,
        "whisper_only": {
            "text": whisper_text,
            "time_s": round(whisper_time, 3),
        },
        "whisper_plus_ollama": {
            "text_raw": whisper_text_2,
            "text_corrected": corrected_text,
            "whisper_time_s": round(whisper_time_2, 3),
            "ollama_time_s": round(ollama_time, 3),
            "total_time_s": round(total_time_with_ollama, 3),
        },
        "user_rating_whisper_only": None,
        "user_rating_with_ollama": None,
    }

    # Ask for user ratings
    print("\n" + "-"*50)
    print("YOUR RATING (1-5, or skip with Enter)")
    print("-"*50)

    try:
        rating1 = input("\nRate Whisper ONLY quality (1-5): ").strip()
        if rating1:
            result["user_rating_whisper_only"] = int(rating1)
    except:
        pass

    try:
        rating2 = input("Rate Whisper + Ollama quality (1-5): ").strip()
        if rating2:
            result["user_rating_with_ollama"] = int(rating2)
    except:
        pass

    return result

def print_final_summary(results):
    """Print final benchmark summary."""
    if not results:
        print("\nNo results to summarize.")
        return

    print("\n" + "="*60)
    print("FINAL BENCHMARK SUMMARY")
    print("="*60)

    # Calculate averages
    whisper_times = [r["whisper_only"]["time_s"] for r in results]
    ollama_times = [r["whisper_plus_ollama"]["ollama_time_s"] for r in results]
    total_times = [r["whisper_plus_ollama"]["total_time_s"] for r in results]
    audio_durations = [r["audio_duration_s"] for r in results]

    avg_whisper = sum(whisper_times) / len(whisper_times)
    avg_ollama = sum(ollama_times) / len(ollama_times)
    avg_total = sum(total_times) / len(total_times)
    avg_audio = sum(audio_durations) / len(audio_durations)

    print(f"\nTests completed: {len(results)}")
    print(f"Average audio duration: {avg_audio:.1f}s")

    print("\n| Metric | Average | Min | Max |")
    print("|--------|---------|-----|-----|")
    print(f"| Whisper inference | {avg_whisper:.2f}s | {min(whisper_times):.2f}s | {max(whisper_times):.2f}s |")
    print(f"| Ollama correction | {avg_ollama:.2f}s | {min(ollama_times):.2f}s | {max(ollama_times):.2f}s |")
    print(f"| Total (with Ollama) | {avg_total:.2f}s | {min(total_times):.2f}s | {max(total_times):.2f}s |")

    # User ratings
    ratings_whisper = [r["user_rating_whisper_only"] for r in results if r["user_rating_whisper_only"]]
    ratings_ollama = [r["user_rating_with_ollama"] for r in results if r["user_rating_with_ollama"]]

    if ratings_whisper or ratings_ollama:
        print("\n| Quality Rating | Average |")
        print("|----------------|---------|")
        if ratings_whisper:
            print(f"| Whisper only | {sum(ratings_whisper)/len(ratings_whisper):.1f}/5 |")
        if ratings_ollama:
            print(f"| With Ollama | {sum(ratings_ollama)/len(ratings_ollama):.1f}/5 |")

    # Recommendation
    print("\n" + "-"*60)
    print("RECOMMENDATION FOR README")
    print("-"*60)
    print(f"\n| Metric | Value |")
    print(f"|--------|-------|")
    print(f"| Whisper inference | ~{avg_whisper:.1f}s |")
    print(f"| Grammar correction | ~{avg_ollama:.1f}s |")
    print(f"| Total latency (with grammar) | ~{avg_total:.1f}s |")
    print(f"| Total latency (without grammar) | ~{avg_whisper:.1f}s |")

    # Save results to file
    filename = f"benchmark_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to: {filename}")

def main():
    print("="*60)
    print("LocalWhisper Interactive Benchmark")
    print("="*60)
    print(f"\nModel: {config.WHISPER_MODEL_SIZE}")
    print(f"Device: {config.DEVICE}")
    print(f"Ollama model: {config.OLLAMA_MODEL}")

    # Check Ollama
    print("\nChecking Ollama...")
    try:
        url = config.OLLAMA_URL.replace("/api/generate", "")
        requests.get(url, timeout=2)
        print("Ollama: OK")
    except:
        print("WARNING: Ollama not running! Grammar correction will fail.")
        print("Start Ollama with: ollama serve")

    # Load Whisper model
    print("\nLoading Whisper model...")
    from faster_whisper import WhisperModel

    start = time.perf_counter()
    model = WhisperModel(
        config.WHISPER_MODEL_SIZE,
        device=config.DEVICE,
        compute_type=config.COMPUTE_TYPE,
        download_root=config.MODELS_DIR,
    )
    load_time = time.perf_counter() - start
    print(f"Model loaded in {load_time:.1f}s")

    # Warm up Ollama
    print("\nWarming up Ollama...")
    try:
        requests.post(config.OLLAMA_URL, json={
            "model": config.OLLAMA_MODEL,
            "prompt": "hello",
            "stream": False
        }, timeout=30)
        print("Ollama: Warmed up")
    except Exception as e:
        print(f"Ollama warmup failed: {e}")

    print("\n" + "="*60)
    print("INSTRUCTIONS")
    print("="*60)
    print("""
1. Each cycle: you speak, we measure, you rate
2. Speak naturally (French, English, or Franglais)
3. Press ENTER when done speaking
4. Rate the quality 1-5 after each test
5. Do 3-5 cycles for good averages
6. Type 'q' to quit and see final summary
""")

    results = []
    cycle = 1

    while True:
        try:
            choice = input(f"\nPress ENTER to start cycle {cycle} (or 'q' to quit): ").strip().lower()
            if choice == 'q':
                break

            result = run_test_cycle(model, cycle)
            if result:
                results.append(result)
                cycle += 1

        except KeyboardInterrupt:
            print("\n\nInterrupted by user.")
            break

    print_final_summary(results)

if __name__ == "__main__":
    main()
