from faster_whisper import WhisperModel
import config
import os
import time

class Transcriber:
    def __init__(self):
        print(f"Loading Whisper Model: {config.WHISPER_MODEL_SIZE} on {config.DEVICE}...")
        start = time.time()
        self.model = WhisperModel(
            config.WHISPER_MODEL_SIZE, 
            device=config.DEVICE, 
            compute_type=config.COMPUTE_TYPE,
            download_root=config.MODELS_DIR
        )
        print(f"Model loaded in {time.time() - start:.2f}s")

    def transcribe(self, audio_data, language=None):
        """
        Transcribe raw audio data (numpy array).
        """
        # Faster-whisper expects float32
        if audio_data.dtype != "float32":
            audio_data = audio_data.astype("float32")

        # Use passed language (or None for auto)
        segments,info = self.model.transcribe(audio_data, beam_size=5, language=language, task="transcribe")
        
        # Collect all text
        text = " ".join([segment.text for segment in segments])
        return text.strip()

if __name__ == "__main__":
    t = Transcriber()
    # Mock audio
    import numpy as np
    audio = np.zeros(16000*2, dtype=np.float32)
    print(t.transcribe(audio))
