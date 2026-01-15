import sounddevice as sd
import numpy as np
import onnxruntime
import config
import threading
import time
import os
import requests
from core.settings import manager as settings
from core.logger import log

class AudioEngine:
    def __init__(self):
        self.sample_rate = config.SAMPLE_RATE
        self.vad_model_path = os.path.join(config.BASE_DIR, "silero_vad.onnx")
        self.download_vad_if_needed()
        self._running = False
        
        # Metering State
        self._metering = False
        self._current_vol = 0.0
        self._meter_stream = None
        
        # Force CPU for VAD
        try:
            self.vad_session = onnxruntime.InferenceSession(self.vad_model_path, providers=['CPUExecutionProvider'])
        except Exception as e:
            log(f"Error loading VAD model: {e}", "error")
            self.download_vad_if_needed()
            self.vad_session = onnxruntime.InferenceSession(self.vad_model_path, providers=['CPUExecutionProvider'])
            
    def get_devices(self):
        return sd.query_devices()

    # --- Optimised Metering ---
    def start_metering(self):
        """Starts a background thread/stream for volume metering."""
        if self._metering: return
        self._metering = True
        
        def meter_callback(indata, frames, time, status):
            if status:
                print(status)
            vol = np.sqrt(np.mean(indata**2))
            self._current_vol = vol * 50 # Scale up

        try:
            device_idx = settings.get("input_device_index")
            # We use a persistent stream instead of opening/closing
            self._meter_stream = sd.InputStream(
                callback=meter_callback,
                channels=1,
                samplerate=self.sample_rate,
                device=device_idx,
                blocksize=1024
            )
            self._meter_stream.start()
            log("Metering started.", "info")
        except Exception as e:
            log(f"Metering Error: {e}", "error")
            self._metering = False

    def stop_metering(self):
        """Stops the metering stream."""
        if self._meter_stream:
            self._meter_stream.stop()
            self._meter_stream.close()
            self._meter_stream = None
        self._metering = False
        self._current_vol = 0.0
        log("Metering stopped.", "info")

    def get_current_volume(self):
        """Returns the cached volume level (Instant)."""
        return self._current_vol
    # --------------------------

    def download_vad_if_needed(self):
         if not os.path.exists(self.vad_model_path) or os.path.getsize(self.vad_model_path) < 1000000:
            url = "https://github.com/snakers4/silero-vad/raw/v4.0/files/silero_vad.onnx"
            try:
                headers = {'User-Agent': 'Mozilla/5.0'}
                r = requests.get(url, headers=headers, allow_redirects=True)
                if r.status_code == 200 and len(r.content) > 1000000:
                    with open(self.vad_model_path, 'wb') as f:
                        f.write(r.content)
            except Exception:
                pass

    def _vad_iterator(self, audio_chunk, h, c):
        input_data = audio_chunk[np.newaxis, :].astype(np.float32)
        sr_data = np.array(self.sample_rate, dtype=np.int64)
        
        ort_inputs = {
            self.vad_session.get_inputs()[0].name: input_data,
            self.vad_session.get_inputs()[1].name: sr_data,
            self.vad_session.get_inputs()[2].name: h,
            self.vad_session.get_inputs()[3].name: c
        }
        ort_outs = self.vad_session.run(None, ort_inputs)
        out, h, c = ort_outs
        return out[0][0], h, c

    def stop_recording(self):
        self._running = False

    def listen_single_segment(self):
        self._running = True
        CHUNK_SIZE = 512
        
        threshold = settings.get("vad_threshold")
        silence_dur = settings.get("silence_duration")
        device_idx = settings.get("input_device_index") 
        
        chunks_per_sec = self.sample_rate / CHUNK_SIZE
        silence_chunks = int(silence_dur * chunks_per_sec)
        
        h = np.zeros((2, 1, 64), dtype=np.float32)
        c = np.zeros((2, 1, 64), dtype=np.float32)
        
        triggered = False
        temp_buffer = []
        ring_buffer = [] 
        ring_buffer_size = 30
        silence_counter = 0
        
        log(f"Listening loop started (Thresh: {threshold:.2f})", "debug")
        print(f"Listening (VAD: {threshold})...")
        
        try:
            with sd.InputStream(samplerate=self.sample_rate, device=device_idx, channels=1, blocksize=CHUNK_SIZE) as stream:
                while self._running:
                    data, overflowed = stream.read(CHUNK_SIZE)
                    data = data.flatten()
                    
                    speech_prob, h, c = self._vad_iterator(data, h, c)
                    
                    if not triggered:
                        ring_buffer.append(data)
                        if len(ring_buffer) > ring_buffer_size:
                            ring_buffer.pop(0)
                        
                        if speech_prob > threshold:
                            print(f"Voice: {speech_prob:.2f}")
                            triggered = True
                            temp_buffer.extend(ring_buffer)
                            temp_buffer.append(data)
                            silence_counter = 0
                    else:
                        temp_buffer.append(data)
                        if speech_prob < threshold:
                            silence_counter += 1
                        else:
                            silence_counter = 0
                            
                        if silence_counter > silence_chunks:
                            print("Silence.")
                            break
                            
            if not self._running:
                log("Recording interrupted.", "info")
                return np.array([], dtype=np.float32)
                
            return np.concatenate(temp_buffer)
        except Exception as e:
            log(f"Recording Exception: {e}", "error")
            print(f"Recording Error: {e}")
            time.sleep(1)
            return np.array([], dtype=np.float32)

if __name__ == "__main__":
    eng = AudioEngine()
    eng.start_metering()
    time.sleep(2)
    print(eng.get_current_volume())
    eng.stop_metering()
