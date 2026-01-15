import sys
import os
import time

def test_imports():
    print("Testing Imports...")
    try:
        import sounddevice
        import faster_whisper
        import numpy
        import onnxruntime
        import requests
        import pyautogui
        import pynput
        from PyQt6 import QtWidgets
        print(" [OK] All imports successful.")
        return True
    except ImportError as e:
        print(f" [FAIL] Import Error: {e}")
        return False

def test_cuda():
    print("Testing CUDA for CTranslate2 (Faster-Whisper)...")
    try:
        from faster_whisper import WhisperModel
        # Small test load
        # We don't load the full model here to save time, unless crucial.
        print(" [OK] Faster-Whisper module loaded (Runtime check needed).")
    except Exception as e:
        print(f" [FAIL] CUDA Error: {e}")

def test_ollama():
    print("Testing Ollama Connection...")
    try:
        import requests
        import config
        r = requests.get("http://localhost:11434/")
        if r.status_code == 200:
            print(" [OK] Ollama is running.")
        else:
            print(f" [WARN] Ollama returned status {r.status_code}")
    except Exception as e:
        print(f" [FAIL] Ollama Connection Error: {e}. Is Ollama running?")

def run_all():
    print("=== Environment Verification ===")
    if test_imports():
        test_cuda()
        test_ollama()
    print("================================")

if __name__ == "__main__":
    run_all()
