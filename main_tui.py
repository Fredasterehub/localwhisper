import sys
import os

# Fix for 4K/High-DPI displays (might matter for terminal emulators on Windows)
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1" 

# Add venv paths if needed (copied from main.py)
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

from core.setup import resolve_ollama_model
from core.settings import manager as settings
import config

from tui.app import WhisperTui

if __name__ == "__main__":
    # Ensure model is ready
    model_name = resolve_ollama_model()
    config.OLLAMA_MODEL = model_name
    
    app = WhisperTui()
    app.run()
