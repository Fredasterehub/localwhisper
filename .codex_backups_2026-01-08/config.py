import os

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

# Audio Settings
SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_SIZE = 512  # Audio chunk size
VAD_THRESHOLD = 0.5  # Voice Activity Detection confidence threshold

# Whisper Settings
WHISPER_MODEL_SIZE = "large-v3"
# "float16" for GPU (requires VRAM), "int8" for efficiency if needed
COMPUTE_TYPE = "int8" # Optimized for Speed/VRAM 
DEVICE = "cuda" # or "cpu"

# Ollama Settings
USE_INTELLIGENCE = True # Set to True to enable Grammar Fixing (Mistral/Llama)
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "mistral" # User requested Mistral (Fast/Good Grammar)

# Input Settings
HOTKEY = "<ctrl>+<alt>+w" # Default hotkey
