from core.audio import AudioEngine
import time
import os

print("--- Testing Audio Engine ---")
if os.path.exists("silero_vad.onnx"):
    print(f"Existing VAD size: {os.path.getsize('silero_vad.onnx')} bytes")

try:
    eng = AudioEngine()
    print("AudioEngine initialized successfully.")
    print(f"VAD Provider: {eng.vad_session.get_providers()}")
except Exception as e:
    print(f"AudioEngine Failed: {e}")
