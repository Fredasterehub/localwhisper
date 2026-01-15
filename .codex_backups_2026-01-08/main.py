import sys
import threading
import queue
import time
import config
import os
import glob
import subprocess
import requests
from pynput import keyboard

# Fix for 4K/High-DPI displays
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_SCALE_FACTOR"] = "1"

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

import faster_whisper
import huggingface_hub

from core.audio import AudioEngine
from core.transcriber import Transcriber
from core.intelligence import IntelligenceEngine
from core.injector import Injector
from core.settings import manager as settings
from core.logger import log 
from ui.overlay import run_overlay
from ui.settings_dialog import SettingsDialog
from PyQt6.QtWidgets import QApplication

def resolve_ollama_model():
    """
    Checks for Llama 3 models and returns the EXACT name installed.
    If none, pulls 'llama3'.
    """
    url = config.OLLAMA_URL.replace("/api/generate", "") # Root URL
    wanted_model = config.OLLAMA_MODEL # "llama3"
    
    # 1. Ensure Server
    try:
        requests.get(url, timeout=0.5)
    except Exception:
        log("Starting Ollama...", "info")
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.Popen(["ollama", "serve"], startupinfo=startupinfo)
            for _ in range(20):
                try:
                    requests.get(url, timeout=0.5)
                    break
                except:
                    time.sleep(1)
        except Exception:
            pass

    # 2. Find Exact Model Name
    try:
        tags = requests.get(f"{url}/api/tags").json()
        models = [m['name'] for m in tags.get('models', [])]
        
        # Priority 1: Exact Match
        if wanted_model in models:
            log(f"Model '{wanted_model}' found.", "info")
            return wanted_model
            
        # Priority 2: Fuzzy Match (e.g. 'llama3.2:latest')
        for m in models:
            if wanted_model in m: # Match 'mistral' in 'mistral:latest'
                log(f"Model '{m}' found (Matched '{wanted_model}').", "info")
                return m
                
        # Priority 3: Not Found -> Pull
        log(f"Model '{wanted_model}' missing. Downloading... (Check new window)", "warning")
        print(f"Downloading {wanted_model}... Check the popup terminal.")
        
        # BLOCKING Pull - Visible Window so user sees progress
        # CREATE_NEW_CONSOLE = 0x00000010
        subprocess.run(["ollama", "pull", wanted_model], creationflags=0x00000010, check=True)
        return wanted_model
        
    except Exception as e:
        log(f"Model Check Error: {e}", "error")
        return wanted_model

def main():
    log("Starting Whisper Flow clone...", "info")
    print("Initializing Core Systems...")
    
    # --- Dynamic Model Resolution ---
    resolved_model = resolve_ollama_model()
    config.OLLAMA_MODEL = resolved_model # Apply Global Config Update
    log(f"Using Intelligence Model: {config.OLLAMA_MODEL}", "info")
    
    # --- Warm-up ---
    threading.Thread(target=lambda: requests.post(config.OLLAMA_URL, json={
        "model": config.OLLAMA_MODEL, 
        "prompt": "hi", 
        "stream": False
    }), daemon=True).start()
    
    app = QApplication(sys.argv)
    ui_queue = queue.Queue()
    
    try:
        audio = AudioEngine()
        transcriber = Transcriber()
        # Pass resolved model explicitly if needed, but config is updated
        intelligence = IntelligenceEngine() 
        injector = Injector()
        log("All systems ready.", "info")
        print("All systems ready.")
    except Exception as e:
        log(f"Init Error: {e}", "error")
        sys.exit(1)

    processing_lock = threading.Lock()
    stop_processing_flag = False
    
    def pipeline_worker():
        nonlocal stop_processing_flag
        while True:
            mode = settings.get("mode")
            if stop_processing_flag:
                time.sleep(0.5)
                continue
            
            if mode != "voice_activation":
                time.sleep(0.1)
                continue
                
            with processing_lock:
                 ui_queue.put("LISTENING")
                 try:
                     audio_data = audio.listen_single_segment() # Blocks
                     if stop_processing_flag or len(audio_data) == 0:
                         ui_queue.put("IDLE")
                         if len(audio_data) == 0: time.sleep(0.1)
                         continue
                 except Exception:
                     ui_queue.put("IDLE")
                     time.sleep(1)
                     continue

                 ui_queue.put("PROCESSING")
                 start_process = time.time()
                 try:
                     lang_code = settings.get("transcription_language")
                     if lang_code == "auto": lang_code = None
                     
                     raw_text = transcriber.transcribe(audio_data, language=lang_code)
                     if raw_text:
                         # log(f"Raw ({time.time()-start_process:.2f}s): {raw_text}", "debug")
                         
                         if settings.get("use_intelligence"):
                             final_text = intelligence.refine_text(raw_text)
                         else:
                             final_text = raw_text # Raw Mode
                             
                         # log(f"Final: {final_text}", "info")
                         
                         injector.type_text(final_text)
                         ui_queue.put("SUCCESS")
                         time.sleep(1.0)
                     else:
                         pass 
                 except Exception as e:
                      log(f"Pipeline Error: {e}", "error")
                 
                 ui_queue.put("IDLE")

    worker_thread = threading.Thread(target=pipeline_worker, daemon=True)
    worker_thread.start()

    def trigger_ptt_pass():
        def _job():
            if processing_lock.acquire(blocking=False):
                try:
                    ui_queue.put("LISTENING")
                    audio_data = audio.listen_single_segment()
                    if len(audio_data) > 0:
                        ui_queue.put("PROCESSING")
                        lang_code = settings.get("transcription_language")
                        if lang_code == "auto": lang_code = None
                        
                        raw_text = transcriber.transcribe(audio_data, language=lang_code)
                        if raw_text:
                            final_text = intelligence.refine_text(raw_text)
                        else:
                            final_text = raw_text # Raw Mode
                            ui_queue.put("SUCCESS")
                            time.sleep(1)
                except Exception:
                    pass
                finally:
                    ui_queue.put("IDLE")
                    processing_lock.release()
        threading.Thread(target=_job, daemon=True).start()

    def on_settings_click():
        nonlocal stop_processing_flag
        stop_processing_flag = True
        if audio: audio.stop_recording()
        time.sleep(0.5) 
        try:
            SettingsDialog(audio).exec()
        except Exception: pass
        stop_processing_flag = False

    if not settings.get("setup_completed"):
        try:
            SettingsDialog(audio).exec()
        except Exception: pass

    # Hotkey Logic (Cleaned up)
    def on_activate():
        if settings.get("mode") == "push_to_talk":
             trigger_ptt_pass()

    def start_hotkey():
        try:
            l = keyboard.GlobalHotKeys({config.HOTKEY: on_activate})
            l.start()
            l.join()
        except: pass
    
    threading.Thread(target=start_hotkey, daemon=True).start()

    def on_quit():
        stop_processing_flag = True
        if audio: audio.stop_recording()
        os._exit(0)

    ui_queue.put("IDLE")
    run_overlay(ui_queue, on_settings_click, app)
    on_quit()

if __name__ == "__main__":
    main()
