import sounddevice as sd
import numpy as np
import onnxruntime
import config
import threading
import time
import os
import requests
import math
from core.settings import manager as settings
from core.logger import log

class AudioEngine:
    def __init__(self):
        self.sample_rate = config.SAMPLE_RATE
        if self.sample_rate != 16000:
            log(f"Silero VAD ONNX is tuned for 16kHz; current SAMPLE_RATE={self.sample_rate}.", "warning")
        self.vad_model_path = os.path.join(config.BASE_DIR, "silero_vad.onnx")
        self.download_vad_if_needed()
        self._running = False
        
        # Metering State
        self._metering = False
        self._current_vol = 0.0
        self._current_speech_prob = 0.0
        self._meter_stream = None
        self._meter_h = None
        self._meter_c = None
        
        # Shared Amplitude for UI Visuals (0.0 - 1.0 approx)
        self.current_amplitude = 0.0

        # Voice-activation state (cooldown)
        self._next_allowed_start_time = 0.0

        # Serialize VAD inference across threads (metering vs recording)
        self._vad_lock = threading.Lock()
        self._meter_was_running = False
        
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
            self._current_vol = vol * 50 # Scale up for Settings Dialog
            self.current_amplitude = min(1.0, vol * 10) # Normalized roughly for Visuals

            try:
                # Estimate VAD speech probability for calibration in Settings UI.
                # Uses a separate Silero state than the recording path.
                if self._meter_h is None or self._meter_c is None:
                    self._meter_h = np.zeros((2, 1, 64), dtype=np.float32)
                    self._meter_c = np.zeros((2, 1, 64), dtype=np.float32)

                chunk = indata.reshape(-1).astype(np.float32)
                speech_prob, self._meter_h, self._meter_c = self._vad_iterator(chunk, self._meter_h, self._meter_c)
                self._current_speech_prob = float(speech_prob)
            except Exception:
                # Never let UI metering crash audio callback.
                pass

        try:
            device_idx = settings.get("input_device_index")
            # We use a persistent stream instead of opening/closing
            self._meter_stream = sd.InputStream(
                callback=meter_callback,
                channels=1,
                samplerate=self.sample_rate,
                device=device_idx,
                blocksize=512,
                dtype="float32",
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
        self._current_speech_prob = 0.0
        self._meter_h = None
        self._meter_c = None
        log("Metering stopped.", "info")

    def get_current_volume(self):
        """Returns the cached volume level (Instant)."""
        return self._current_vol

    def get_current_speech_prob(self):
        """Returns the cached Silero speech probability [0..1]."""
        return self._current_speech_prob
    # --------------------------

    def download_vad_if_needed(self):
        if not os.path.exists(self.vad_model_path) or os.path.getsize(self.vad_model_path) < 1000000:
            url = "https://github.com/snakers4/silero-vad/raw/v4.0/files/silero_vad.onnx"
            try:
                headers = {'User-Agent': 'Mozilla/5.0'}
                r = requests.get(url, headers=headers, allow_redirects=True, timeout=10)
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
        with self._vad_lock:
            ort_outs = self.vad_session.run(None, ort_inputs)
        out, h, c = ort_outs
        return out[0][0], h, c

    def stop_recording(self):
        self._running = False

    def _pause_metering_if_needed(self):
        if self._metering and self._meter_stream:
            try:
                self._meter_stream.stop()
                self._meter_was_running = True
            except Exception:
                self._meter_was_running = False
        else:
            self._meter_was_running = False

    def _resume_metering_if_needed(self):
        if self._meter_was_running and self._meter_stream:
            try:
                self._meter_stream.start()
            except Exception:
                pass
        self._meter_was_running = False

    @staticmethod
    def _rms_dbfs(samples: np.ndarray) -> float:
        # dB relative to full-scale for float audio in [-1..1].
        rms = float(np.sqrt(np.mean(samples * samples))) if samples.size else 0.0
        return 20.0 * math.log10(max(rms, 1e-8))

    def listen_single_segment(self):
        self._running = True
        CHUNK_SIZE = int(getattr(config, "BLOCK_SIZE", 512))
        if self.sample_rate == 16000 and CHUNK_SIZE != 512:
            log(f"Silero VAD expects 512 samples at 16kHz; overriding BLOCK_SIZE={CHUNK_SIZE} -> 512.", "warning")
            CHUNK_SIZE = 512

        threshold = float(settings.get("vad_threshold"))
        silence_dur = settings.get("silence_duration")
        device_idx = settings.get("input_device_index") 

        start_confirm_ms = int(settings.get("voice_activation_start_confirm_ms"))
        hangover_ms = int(settings.get("voice_activation_hangover_ms"))
        cooldown_ms = int(settings.get("voice_activation_cooldown_ms"))
        pre_roll_ms = int(settings.get("voice_activation_pre_roll_ms"))
        min_segment_ms = int(settings.get("voice_activation_min_segment_ms"))
        min_speech_ms = int(settings.get("voice_activation_min_speech_ms"))
        max_segment_s = float(settings.get("voice_activation_max_segment_s"))
        start_speech_prob = float(settings.get("voice_activation_start_speech_prob"))
        stop_speech_prob = float(settings.get("voice_activation_stop_speech_prob"))
        start_db_margin = float(settings.get("voice_activation_start_db_margin"))
        stop_db_margin = float(settings.get("voice_activation_stop_db_margin"))
        noise_update_speech_prob = float(settings.get("voice_activation_noise_update_speech_prob"))
        noise_ema_alpha = float(settings.get("voice_activation_noise_ema_alpha"))

        # Backwards-compatible: allow the legacy single threshold to still affect gating.
        start_speech_prob = max(start_speech_prob, threshold)
        stop_speech_prob = min(stop_speech_prob, start_speech_prob - 0.08) if stop_speech_prob >= start_speech_prob else stop_speech_prob

        chunk_ms = (CHUNK_SIZE / self.sample_rate) * 1000.0
        start_confirm_chunks = max(1, int(math.ceil(start_confirm_ms / chunk_ms)))

        h = np.zeros((2, 1, 64), dtype=np.float32)
        c = np.zeros((2, 1, 64), dtype=np.float32)

        triggered = False
        temp_buffer = []
        ring_buffer = [] 
        ring_buffer_size = max(1, int(math.ceil(pre_roll_ms / chunk_ms)))

        # Adaptive noise floor (dBFS)
        # Updates only while ARMED (not recording) and not in a start-candidate streak.
        noise_floor_db = -55.0
        noise_floor_db = float(max(-80.0, min(-20.0, noise_floor_db)))
        start_candidate_count = 0
        speech_ms = 0.0
        trigger_start_time = 0.0
        last_speech_time = 0.0
        max_speech_prob = 0.0
        max_rms_db = -120.0

        now = time.time()
        if now < self._next_allowed_start_time:
            time.sleep(max(0.0, self._next_allowed_start_time - now))

        try:
            self._pause_metering_if_needed()
            with sd.InputStream(
                samplerate=self.sample_rate,
                device=device_idx,
                channels=1,
                blocksize=CHUNK_SIZE,
                dtype="float32",
            ) as stream:
                while self._running:
                    data, overflowed = stream.read(CHUNK_SIZE)
                    data = data.flatten()

                    # RMS Gating (Optimization)
                    # If energy is very low, skip expensive VAD inference
                    rms_db = self._rms_dbfs(data)
                    max_rms_db = max(max_rms_db, float(rms_db))
                    
                    # Update Shared Amplitude for UI
                    # Convert dBFS roughly back to linear 0-1 range for visualizer
                    # -60dB -> 0.0, -0dB -> 1.0
                    lin_amp = max(0.0, (rms_db + 60) / 60)
                    self.current_amplitude = lin_amp 
                    
                    # Heuristic: If we are not in a trigger candidate sequence, and energy is way below floor, skip VAD.
                    # We need a margin below noise floor where we are "sure" it's silence.
                    # noise_floor_db is adaptive, but let's use a hard safety floor too.
                    skip_vad = False
                    if start_candidate_count == 0 and not triggered:
                        # If energy is < noise_floor_db (which is ~ambient) - 5dB, it's definitely silence.
                        if rms_db < (noise_floor_db - 5.0): 
                            skip_vad = True
                            speech_prob = 0.0 # Force 0
                            
                    if not skip_vad:
                         speech_prob, h, c = self._vad_iterator(data, h, c)
                    
                    max_speech_prob = max(max_speech_prob, float(speech_prob))

                    if not triggered:
                        ring_buffer.append(data)
                        if len(ring_buffer) > ring_buffer_size:
                            ring_buffer.pop(0)

                        # Update baseline noise floor only when we're not in speech and not already trending toward a trigger.
                        if start_candidate_count == 0 and speech_prob <= noise_update_speech_prob:
                            noise_floor_db = (1.0 - noise_ema_alpha) * noise_floor_db + noise_ema_alpha * rms_db
                            noise_floor_db = float(max(-80.0, min(-20.0, noise_floor_db)))

                        # Start gate: require sustained speech probability AND energy above baseline.
                        start_gate = (speech_prob >= start_speech_prob) and (rms_db >= (noise_floor_db + start_db_margin))
                        if start_gate:
                            start_candidate_count += 1
                        else:
                            start_candidate_count = 0

                        if start_candidate_count >= start_confirm_chunks:
                            triggered = True
                            trigger_start_time = time.time()
                            last_speech_time = trigger_start_time
                            temp_buffer.extend(ring_buffer)
                            speech_ms = start_confirm_chunks * chunk_ms
                    else:
                        temp_buffer.append(data)

                        # Track "speech present" with hysteresis + energy margin.
                        speech_present = (speech_prob >= stop_speech_prob) or (rms_db >= (noise_floor_db + stop_db_margin))
                        if speech_present:
                            last_speech_time = time.time()
                            speech_ms += chunk_ms
                        # While recording, do NOT update baseline (prevents music from "teaching" the baseline mid-utterance).

                        # Stop gate: end after sustained silence + hangover.
                        effective_silence_s = float(silence_dur) + (hangover_ms / 1000.0)
                        if (time.time() - last_speech_time) >= effective_silence_s:
                            break

                        # Safety: prevent infinite segments on continuous background noise.
                        if (time.time() - trigger_start_time) >= max_segment_s:
                            log("Max segment duration reached; cutting segment.", "warning")
                            break

            if not self._running:
                log("Recording interrupted.", "info")
                return np.array([], dtype=np.float32)

            # Reject very short or likely-false triggers.
            total_ms = (time.time() - trigger_start_time) * 1000.0 if triggered else 0.0
            if (not triggered) or (total_ms < min_segment_ms) or (speech_ms < min_speech_ms):
                self._next_allowed_start_time = time.time() + (cooldown_ms / 1000.0)
                return np.array([], dtype=np.float32)

            self._next_allowed_start_time = time.time() + (cooldown_ms / 1000.0)
            audio = np.concatenate(temp_buffer).astype(np.float32)

            if settings.get("voice_activation_debug"):
                dur_s = float(len(audio) / self.sample_rate)
                log(
                    f"VAD segment: dur={dur_s:.2f}s max_p={max_speech_prob:.2f} "
                    f"max_rms_db={max_rms_db:.1f} noise_db={noise_floor_db:.1f} "
                    f"speech_ms={speech_ms:.0f}",
                    "info",
                )

            return audio
        except Exception as e:
            log(f"Recording Exception: {e}", "error")
            print(f"Recording Error: {e}")
            time.sleep(1)
            return np.array([], dtype=np.float32)
        finally:
            self._resume_metering_if_needed()

if __name__ == "__main__":
    eng = AudioEngine()
    eng.start_metering()
    time.sleep(2)
    print(eng.get_current_volume())
    eng.stop_metering()
