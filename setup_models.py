import os
import requests
import config
from faster_whisper import WhisperModel

def download_vad():
    vad_path = os.path.join(config.BASE_DIR, "silero_vad.onnx")
    url = "https://github.com/snakers4/silero-vad/raw/v4.0/files/silero_vad.onnx"
    
    print(f"Checking VAD model at {vad_path}...")
    
    if os.path.exists(vad_path) and os.path.getsize(vad_path) > 1000000:
        print(" [OK] VAD model already exists.")
        return

    print(f"Downloading VAD model from {url}...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, stream=True)
        r.raise_for_status()
        
        with open(vad_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        
        if os.path.getsize(vad_path) > 1000000:
            print(" [OK] VAD model downloaded successfully.")
        else:
            print(" [FAIL] Downloaded file is too small (likely HTML). Deleting...")
            os.remove(vad_path)
    except Exception as e:
        print(f" [FAIL] Error downloading VAD: {e}")

def download_whisper():
    print(f"Checking Whisper Model ({config.WHISPER_MODEL_SIZE})...")
    try:
        # This triggers the download if not present
        model = WhisperModel(
            config.WHISPER_MODEL_SIZE, 
            device=config.DEVICE, 
            compute_type=config.COMPUTE_TYPE,
            download_root=config.MODELS_DIR
        )
        print(" [OK] Whisper model is ready.")
    except Exception as e:
        print(f" [FAIL] Error loading/downloading Whisper: {e}")

if __name__ == "__main__":
    print("--- Starting Model Setup ---")
    download_vad()
    # verify directory creation
    if not os.path.exists(config.MODELS_DIR):
        os.makedirs(config.MODELS_DIR)
    download_whisper()
    print("--- Setup Complete ---")
