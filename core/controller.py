import threading
import time
import queue
from core.audio import AudioEngine
from core.transcriber import Transcriber
from core.intelligence import IntelligenceEngine
from core.injector import Injector
from core.settings import manager as settings
from core.logger import log

class CoreController:
    def __init__(self, ui_callback=None):
        self.ui_callback = ui_callback # Function(state: str)
        self.audio = AudioEngine()
        self.transcriber = Transcriber()
        self.intelligence = IntelligenceEngine()
        self.injector = Injector()
        
        self.processing_lock = threading.Lock()
        self.stop_processing_flag = False
        self.running = True
        
        log("CoreController initialized", "info")

    def update_ui(self, state):
        if self.ui_callback:
            self.ui_callback(state)

    def get_success_hold_s(self) -> float:
        try:
            return max(0.05, float(settings.get("success_hold_ms")) / 1000.0)
        except Exception:
            return 0.35

    def should_refine_llm(self, confidence: str, raw_text: str) -> bool:
        if not settings.get("use_intelligence"):
            return False

        try:
            min_audio_s = float(settings.get("llm_refine_min_audio_s"))
            audio_s = float(getattr(self.transcriber, "last_stats", {}).get("audio_seconds", 0.0))
            if audio_s and audio_s < min_audio_s:
                return False
        except Exception:
            pass

        try:
            min_words = int(settings.get("llm_refine_min_words"))
            if min_words > 0:
                wc = len([w for w in (raw_text or "").strip().split() if w])
                if wc < min_words:
                    return False
        except Exception:
            pass

        want = str(settings.get("llm_refine_min_confidence") or "high").lower()
        rank = {"high": 3, "medium": 2, "low": 1, "silence": 0, "unknown": 0}
        return rank.get(confidence, 0) >= rank.get(want, 3)

    def start_pipeline(self):
        worker_thread = threading.Thread(target=self._pipeline_worker, daemon=True)
        worker_thread.start()

    def _pipeline_worker(self):
        while self.running:
            mode = settings.get("mode")
            if self.stop_processing_flag:
                time.sleep(0.5)
                continue
            
            if mode != "voice_activation":
                time.sleep(0.1)
                continue
                
            with self.processing_lock:
                 self.update_ui("LISTENING")
                 try:
                     audio_data = self.audio.listen_single_segment() # Blocks
                     if self.stop_processing_flag or len(audio_data) == 0:
                         self.update_ui("IDLE")
                         if len(audio_data) == 0: time.sleep(0.1)
                         continue
                 except Exception:
                     self.update_ui("IDLE")
                     time.sleep(1)
                     continue

                 self.update_ui("PROCESSING")
                 try:
                     self.process_audio(audio_data)
                 except Exception as e:
                      log(f"Pipeline Error: {e}", "error")
                 
                 self.update_ui("IDLE")

    def process_audio(self, audio_data):
        lang_code = settings.get("transcription_language")
        if lang_code == "auto": lang_code = None
        
        raw_text = self.transcriber.transcribe(audio_data, language=lang_code)
        if raw_text:
            if self.should_refine_llm(getattr(self.transcriber, "last_confidence", "unknown"), raw_text):
                final_text = self.intelligence.refine_text(raw_text)
            else:
                final_text = raw_text 
                
            self.injector.type_text(final_text)
            self.update_ui("SUCCESS")
            time.sleep(self.get_success_hold_s())
        else:
            pass 

    def trigger_ptt(self):
        def _job():
            if self.processing_lock.acquire(blocking=False):
                try:
                    if self.stop_processing_flag:
                        return
                    self.update_ui("LISTENING")
                    audio_data = self.audio.listen_single_segment()
                    if len(audio_data) > 0:
                        self.update_ui("PROCESSING")
                        self.process_audio(audio_data)
                except Exception:
                    pass
                finally:
                    self.update_ui("IDLE")
                    self.processing_lock.release()
        threading.Thread(target=_job, daemon=True).start()

    def shutdown(self):
        self.running = False
        self.stop_processing_flag = True
        if self.audio: self.audio.stop_recording()
