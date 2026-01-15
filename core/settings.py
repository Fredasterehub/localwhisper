import json
import os
import config
from core.logger import log

class SettingsManager:
    def __init__(self):
        self.settings_path = os.path.join(config.BASE_DIR, "user_settings.json")
        self.defaults = {
            "vad_threshold": 0.5,
            "silence_duration": 0.8,
            "mode": "voice_activation", # or "push_to_talk"
            "push_to_talk_key": "space", # placeholder for logic, actual hotkey handled by pynput
            "input_device_index": None, # Default device
            "use_intelligence": False, # Default to Raw Mode (User Preference)
            "transcription_language": "auto", # auto, en, fr

            # Voice-activated mode (Discord-like) tuning
            # Start gate = Silero speech probability + adaptive noise floor (RMS dBFS margin)
            "voice_activation_start_confirm_ms": 220,
            "voice_activation_hangover_ms": 160,
            "voice_activation_cooldown_ms": 350,
            "voice_activation_pre_roll_ms": 550,
            "voice_activation_min_segment_ms": 450,
            "voice_activation_min_speech_ms": 220,
            "voice_activation_max_segment_s": 60.0,
            "voice_activation_start_speech_prob": 0.62,
            "voice_activation_stop_speech_prob": 0.45,
            "voice_activation_start_db_margin": 8.0,
            "voice_activation_stop_db_margin": 4.0,
            "voice_activation_noise_update_speech_prob": 0.20,
            "voice_activation_noise_ema_alpha": 0.04,

            # Transcription stability (faster-whisper decode options)
            "decode_beam_size": 8,
            "decode_temperature": 0.0,
            "decode_best_of": 1,
            "decode_patience": 1.0,
            "decode_length_penalty": 1.0,
            "decode_repetition_penalty": 1.08,
            "decode_no_repeat_ngram_size": 0,
            "decode_condition_on_previous_text": True,
            "decode_no_speech_threshold": 0.6,
            "decode_log_prob_threshold": -1.0,
            "decode_compression_ratio_threshold": 2.35,
            "language_detection_threshold": 0.6,
            "language_detection_segments": 3,

            # Noisy-audio second pass (quality-first, may add ~0.2-1.0s)
            "decode_enable_noisy_second_pass": True,
            "decode_noisy_beam_size": 10,
            "decode_noisy_best_of": 1,
            "decode_noisy_condition_on_previous_text": False,

            # Sticky language (prevents FR/EN flip-flop when language is set to "auto")
            "sticky_language_enabled": True,
            "sticky_language_min_prob": 0.90,
            "sticky_language_ttl_s": 180.0,
            "sticky_language_redetect_interval_s": 60.0,

            # Auto language disambiguation (FR/EN): only triggers extra decode when detection is ambiguous.
            "auto_languages": ["en", "fr"],
            "auto_language_ambiguity_min_prob": 0.88,
            "auto_language_ambiguity_min_margin": 0.12,
            "auto_language_force_on_short_utterance": True,
            "auto_language_short_utterance_s": 2.5,

            # Confidence heuristics (reject likely hallucinations / noise-only captures)
            "reject_no_speech_prob": 0.85,
            "reject_avg_logprob": -0.95,
            "reject_min_chars": 2,

            # Confidence classification thresholds (used to decide retry/LLM/reject)
            "conf_high_min_avg_logprob": -0.55,
            "conf_high_max_avg_no_speech_prob": 0.55,
            "conf_high_max_avg_compression_ratio": 2.05,
            "conf_med_min_avg_logprob": -0.85,
            "conf_med_max_avg_no_speech_prob": 0.78,
            "conf_med_max_avg_compression_ratio": 2.35,

            # Injection behavior
            "inject_typing_max_chars": 32,
            "inject_terminal_always_paste": True,
            "inject_clipboard_settle_ms": 80,
            "inject_clipboard_restore_delay_ms": 550,
            "inject_clipboard_retry_count": 6,
            "inject_clipboard_retry_backoff_ms": 20,
            "terminal_processes": [
                "windowsterminal.exe",
                "wt.exe",
                "conhost.exe",
                "cmd.exe",
                "powershell.exe",
                "pwsh.exe",
                "openconsole.exe",
                "wezterm.exe",
                "alacritty.exe",
                "mintty.exe",
                "tabby.exe",
                "hyper.exe",
                "putty.exe",
            ],
            "paste_hotkey_order": ["ctrl+shift+v", "shift+insert", "ctrl+v"],

            # LLM refinement safety (Ollama)
            "ollama_timeout_s": 6.0,
            "llm_refine_max_chars": 420,
            "llm_refine_skip_code_like": True,
            "llm_refine_min_confidence": "high",  # high|medium|low
            "llm_refine_min_audio_s": 2.5,
            "llm_refine_min_words": 6,

            # Voice activation debug (logs segment summaries)
            "voice_activation_debug": False,

            # UI timing
            "success_hold_ms": 350,

            # Overlay skin
            "overlay_skin": "matrix_rain",  # matrix_rain|dot|sauron_eye

            # Sauron eye skin tuning
            "sauron_fire_fps_ms": 40,
            "setup_completed": False
        }
        self.settings = self.load_settings()

    def _warn_and_prune_unknown_keys(self, raw: dict) -> dict:
        if not isinstance(raw, dict):
            return {}

        known = set(self.defaults.keys())
        unknown = sorted([k for k in raw.keys() if k not in known])
        if unknown:
            log(f"Unknown settings keys ignored: {unknown}", "warning")
        return {k: v for k, v in raw.items() if k in known}

    def load_settings(self):
        if not os.path.exists(self.settings_path):
            return self.defaults.copy()
        
        try:
            with open(self.settings_path, 'r') as f:
                data = json.load(f)
                data = self._warn_and_prune_unknown_keys(data)
                # Merge with defaults to ensure all keys exist
                merged = self.defaults.copy()
                merged.update(data)
                return merged
        except Exception as e:
            print(f"Error loading settings: {e}")
            return self.defaults.copy()

    def save_settings(self):
        try:
            with open(self.settings_path, 'w') as f:
                json.dump(self.settings, f, indent=4)
            print("Settings saved.")
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get(self, key):
        return self.settings.get(key, self.defaults.get(key))

    def set(self, key, value):
        if key not in self.defaults:
            log(f"Attempt to set unknown setting ignored: {key}", "warning")
            return
        self.settings[key] = value
        self.save_settings()

# Global singleton
manager = SettingsManager()
