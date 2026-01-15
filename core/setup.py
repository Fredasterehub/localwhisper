import requests
import subprocess
import time
import config
from core.logger import log

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
