from faster_whisper import WhisperModel
import config
import os
import time
import inspect
from core.settings import manager as settings
from core.logger import log

class Transcriber:
    def __init__(self):
        print(f"Loading Whisper Model: {config.WHISPER_MODEL_SIZE} on {config.DEVICE}...")
        start = time.time()
        self._compute_type_effective = config.COMPUTE_TYPE
        try:
            self.model = WhisperModel(
                config.WHISPER_MODEL_SIZE,
                device=config.DEVICE,
                compute_type=config.COMPUTE_TYPE,
                download_root=config.MODELS_DIR,
            )
        except Exception as e:
            # Explicit fallback for reliability (VRAM/driver issues): retry with int8.
            log(f"Whisper model load failed with compute_type={config.COMPUTE_TYPE}: {e}", "warning")
            self._compute_type_effective = "int8"
            self.model = WhisperModel(
                config.WHISPER_MODEL_SIZE,
                device=config.DEVICE,
                compute_type="int8",
                download_root=config.MODELS_DIR,
            )
        print(f"Model loaded in {time.time() - start:.2f}s (compute_type={self._compute_type_effective})")

        self._sticky_language = None
        self._sticky_set_time = 0.0
        self._last_redetect_time = 0.0
        self._warned_unsupported_args = set()
        self._transcribe_sig = inspect.signature(WhisperModel.transcribe)

        # Last-result metadata for downstream policy (LLM/refuse/etc.)
        self.last_confidence = "unknown"  # high|medium|low|silence|unknown
        self.last_stats = {}

    def _choose_language(self, requested_language: str | None) -> str | None:
        if requested_language:
            return requested_language

        if settings.get("transcription_language") != "auto":
            return settings.get("transcription_language")

        # Auto mode: let Whisper detect language per utterance.
        return None

    def _get_auto_languages(self) -> list[str]:
        langs = settings.get("auto_languages")
        if isinstance(langs, list) and langs:
            out = []
            for x in langs:
                s = str(x).strip().lower()
                if s and s not in out:
                    out.append(s)
            if out:
                return out
        return ["en", "fr"]

    @staticmethod
    def _sorted_language_probs(info) -> list[tuple[str, float]]:
        try:
            probs = getattr(info, "all_language_probs", None)
            if probs:
                return sorted([(str(l).lower(), float(p)) for (l, p) in probs], key=lambda x: x[1], reverse=True)
        except Exception:
            pass
        try:
            return [(str(getattr(info, "language", "")).lower(), float(getattr(info, "language_probability", 0.0)))]
        except Exception:
            return []

    def _is_language_ambiguous(self, info) -> bool:
        """
        Treat language as ambiguous when detection is weak or close.
        This is the main driver for the extra FR/EN forced-decode pass.
        """
        probs = self._sorted_language_probs(info)
        if not probs:
            return True

        top_lang, top_p = probs[0]
        second_p = probs[1][1] if len(probs) > 1 else 0.0

        min_prob = float(settings.get("auto_language_ambiguity_min_prob"))
        min_margin = float(settings.get("auto_language_ambiguity_min_margin"))
        auto_langs = set(self._get_auto_languages())

        if top_lang not in auto_langs:
            return True
        if top_p < min_prob:
            return True
        if (top_p - second_p) < min_margin:
            return True
        return False

    def _maybe_update_sticky_language(self, info, audio_seconds: float):
        if not settings.get("sticky_language_enabled"):
            return

        lang = str(getattr(info, "language", "") or "").lower()
        prob = float(getattr(info, "language_probability", 0.0))
        min_prob = float(settings.get("sticky_language_min_prob"))
        ttl_s = float(settings.get("sticky_language_ttl_s"))
        now = time.time()

        if not lang:
            return

        # For very short utterances, avoid "locking in" on a potentially noisy detection.
        if audio_seconds < 1.0:
            return

        if prob >= min_prob:
            self._sticky_language = lang
            self._sticky_set_time = now
            return

        # If sticky expired, allow updates at lower confidence to recover.
        if self._sticky_language and (now - self._sticky_set_time) > ttl_s:
            if prob >= (min_prob - 0.08):
                self._sticky_language = lang
                self._sticky_set_time = now

    def _validate_and_build_decode_args(self, noisy: bool) -> dict:
        """
        Build a dict of WhisperModel.transcribe kwargs from Settings.
        Enforces: unknown/unsupported args are not silently applied.
        """
        def clamp_int(name: str, value, lo: int, hi: int, default: int) -> int:
            try:
                v = int(value)
            except Exception:
                log(f"Invalid {name}={value!r}; using {default}.", "warning")
                return default
            if v < lo or v > hi:
                log(f"Out-of-range {name}={v}; clamping to [{lo},{hi}].", "warning")
                v = max(lo, min(hi, v))
            return v

        def clamp_float(name: str, value, lo: float, hi: float, default: float) -> float:
            try:
                v = float(value)
            except Exception:
                log(f"Invalid {name}={value!r}; using {default}.", "warning")
                return default
            if v < lo or v > hi:
                log(f"Out-of-range {name}={v}; clamping to [{lo},{hi}].", "warning")
                v = max(lo, min(hi, v))
            return float(v)

        if noisy:
            beam_size = clamp_int("decode_noisy_beam_size", settings.get("decode_noisy_beam_size"), 1, 20, 10)
            best_of = clamp_int("decode_noisy_best_of", settings.get("decode_noisy_best_of"), 1, 10, 1)
            condition_on_previous_text = bool(settings.get("decode_noisy_condition_on_previous_text"))
        else:
            beam_size = clamp_int("decode_beam_size", settings.get("decode_beam_size"), 1, 20, 8)
            best_of = clamp_int("decode_best_of", settings.get("decode_best_of"), 1, 10, 1)
            condition_on_previous_text = bool(settings.get("decode_condition_on_previous_text"))

        temperature = clamp_float("decode_temperature", settings.get("decode_temperature"), 0.0, 1.0, 0.0)
        patience = clamp_float("decode_patience", settings.get("decode_patience"), 0.1, 2.5, 1.0)
        length_penalty = clamp_float("decode_length_penalty", settings.get("decode_length_penalty"), 0.5, 1.5, 1.0)
        repetition_penalty = clamp_float("decode_repetition_penalty", settings.get("decode_repetition_penalty"), 1.0, 1.5, 1.08)
        no_repeat_ngram_size = clamp_int("decode_no_repeat_ngram_size", settings.get("decode_no_repeat_ngram_size"), 0, 10, 0)
        no_speech_threshold = clamp_float("decode_no_speech_threshold", settings.get("decode_no_speech_threshold"), 0.0, 1.0, 0.6)
        log_prob_threshold = clamp_float("decode_log_prob_threshold", settings.get("decode_log_prob_threshold"), -5.0, 0.0, -1.0)
        compression_ratio_threshold = clamp_float("decode_compression_ratio_threshold", settings.get("decode_compression_ratio_threshold"), 1.5, 3.5, 2.35)
        language_detection_threshold = clamp_float("language_detection_threshold", settings.get("language_detection_threshold"), 0.0, 1.0, 0.6)
        language_detection_segments = clamp_int("language_detection_segments", settings.get("language_detection_segments"), 1, 10, 2)

        # Preferred args set (hardcoded whitelist) -> strict validation vs installed faster-whisper.
        desired = {
            "beam_size": beam_size,
            "best_of": best_of,
            "patience": patience,
            "length_penalty": length_penalty,
            "repetition_penalty": repetition_penalty,
            "no_repeat_ngram_size": no_repeat_ngram_size,
            "temperature": temperature,
            "condition_on_previous_text": condition_on_previous_text,
            "no_speech_threshold": no_speech_threshold,
            "log_prob_threshold": log_prob_threshold,
            "compression_ratio_threshold": compression_ratio_threshold,
            "language_detection_threshold": language_detection_threshold,
            "language_detection_segments": language_detection_segments,

            # Always fixed for this app (audio already segmented by VAD).
            "vad_filter": False,
            "word_timestamps": False,
        }

        supported = set(self._transcribe_sig.parameters.keys())
        effective = {}
        unsupported = sorted([k for k in desired.keys() if k not in supported])
        if unsupported:
            for k in unsupported:
                if k not in self._warned_unsupported_args:
                    log(f"Unsupported faster-whisper transcribe arg ignored: {k}", "warning")
                    self._warned_unsupported_args.add(k)

        for k, v in desired.items():
            if k in supported:
                effective[k] = v
        return effective

    def _classify_confidence(self, segments: list, text: str) -> tuple[str, dict]:
        if not segments or not text:
            return "silence", {"reason": "empty"}

        avg_no_speech = sum(float(s.no_speech_prob) for s in segments) / max(1, len(segments))
        avg_logprob = sum(float(s.avg_logprob) for s in segments) / max(1, len(segments))
        avg_compression = sum(float(s.compression_ratio) for s in segments) / max(1, len(segments))

        stats = {
            "avg_no_speech_prob": float(avg_no_speech),
            "avg_logprob": float(avg_logprob),
            "avg_compression_ratio": float(avg_compression),
            "segments": int(len(segments)),
            "chars": int(len(text)),
        }

        # Hard reject: very likely silence + low logprob.
        reject_no_speech_prob = float(settings.get("reject_no_speech_prob"))
        reject_avg_logprob = float(settings.get("reject_avg_logprob"))
        if avg_no_speech >= reject_no_speech_prob and avg_logprob <= reject_avg_logprob:
            return "silence", {**stats, "reason": "no_speech"}

        high = (
            avg_logprob >= float(settings.get("conf_high_min_avg_logprob"))
            and avg_no_speech <= float(settings.get("conf_high_max_avg_no_speech_prob"))
            and avg_compression <= float(settings.get("conf_high_max_avg_compression_ratio"))
        )
        if high:
            return "high", stats

        medium = (
            avg_logprob >= float(settings.get("conf_med_min_avg_logprob"))
            and avg_no_speech <= float(settings.get("conf_med_max_avg_no_speech_prob"))
            and avg_compression <= float(settings.get("conf_med_max_avg_compression_ratio"))
        )
        if medium:
            return "medium", stats

        return "low", stats

    def transcribe(self, audio_data, language=None):
        """
        Transcribe raw audio data (numpy array).
        """
        # Faster-whisper expects float32
        if audio_data.dtype != "float32":
            audio_data = audio_data.astype("float32")

        chosen_language = self._choose_language(language)

        base_args = self._validate_and_build_decode_args(noisy=False)
        segments, info = self.model.transcribe(
            audio_data,
            task="transcribe",
            language=chosen_language,
            **base_args,
        )

        segments = list(segments)
        text = " ".join([segment.text for segment in segments]).strip()

        confidence, stats = self._classify_confidence(segments, text)
        audio_seconds = float(len(audio_data) / float(getattr(config, "SAMPLE_RATE", 16000))) if hasattr(audio_data, "__len__") else 0.0
        stats = {**stats, "audio_seconds": audio_seconds}
        self.last_confidence = confidence
        self.last_stats = stats

        min_chars = int(settings.get("reject_min_chars"))
        if len(text) < min_chars:
            self.last_confidence = "silence"
            self.last_stats = {**stats, "reason": "too_short"}
            return ""

        # Optional quality-first second pass when the first decode looks noisy.
        if confidence == "low" and settings.get("decode_enable_noisy_second_pass"):
            noisy_args = self._validate_and_build_decode_args(noisy=True)
            segments2, info2 = self.model.transcribe(
                audio_data,
                task="transcribe",
                language=chosen_language,
                **noisy_args,
            )
            segments2 = list(segments2)
            text2 = " ".join([s.text for s in segments2]).strip()
            conf2, stats2 = self._classify_confidence(segments2, text2)

            # Choose the higher-confidence result; tie-breaker by avg_logprob.
            rank = {"high": 3, "medium": 2, "low": 1, "silence": 0, "unknown": 0}
            choose_second = False
            if rank.get(conf2, 0) > rank.get(confidence, 0):
                choose_second = True
            elif conf2 == confidence:
                if stats2.get("avg_logprob", -9) > stats.get("avg_logprob", -9):
                    choose_second = True

            if choose_second:
                segments, text, confidence, stats = segments2, text2, conf2, stats2
                info = info2
                self.last_confidence = confidence
                self.last_stats = {**stats, "audio_seconds": audio_seconds, "pass": "noisy_second"}
            else:
                self.last_stats = {**stats, "audio_seconds": audio_seconds, "pass": "base"}

        if self.last_confidence in {"silence", "low"}:
            # Quality > latency: do not inject low-confidence text.
            return ""

        # Auto language stabilization (FR/EN): if language detection is ambiguous, decode again with forced languages
        # and choose the one with better confidence.
        if chosen_language is None and settings.get("transcription_language") == "auto":
            force_on_short = bool(settings.get("auto_language_force_on_short_utterance"))
            short_s = float(settings.get("auto_language_short_utterance_s"))
            short_utterance = force_on_short and (audio_seconds > 0.0) and (audio_seconds <= short_s)

            # Always disambiguate if the detected language is not in our allowed auto set.
            top_lang = str(getattr(info, "language", "") or "").lower()
            auto_langs = set(self._get_auto_languages())
            not_allowed_lang = bool(top_lang) and (top_lang not in auto_langs)

            if short_utterance or not_allowed_lang or self._is_language_ambiguous(info):
                auto_langs = self._get_auto_languages()
                # Prefer sticky language first (helps prevent random flips on short utterances).
                if self._sticky_language and self._sticky_language in auto_langs:
                    ordered = [self._sticky_language] + [l for l in auto_langs if l != self._sticky_language]
                else:
                    ordered = auto_langs

                # Use the same args as the selected pass (base/noisy).
                args = noisy_args if self.last_stats.get("pass") == "noisy_second" else base_args
                best = ({"high": 3, "medium": 2, "low": 1, "silence": 0, "unknown": 0}.get(self.last_confidence, 0), stats.get("avg_logprob", -9.0), text, segments, info, getattr(info, "language", None))

                for lang in ordered[:2]:
                    seg_l, info_l = self.model.transcribe(
                        audio_data,
                        task="transcribe",
                        language=lang,
                        **args,
                    )
                    seg_l = list(seg_l)
                    text_l = " ".join([s.text for s in seg_l]).strip()
                    conf_l, stats_l = self._classify_confidence(seg_l, text_l)
                    stats_l = {**stats_l, "audio_seconds": audio_seconds}
                    score = ({"high": 3, "medium": 2, "low": 1, "silence": 0, "unknown": 0}.get(conf_l, 0), stats_l.get("avg_logprob", -9.0), text_l, seg_l, info_l, lang)
                    if score[0] > best[0] or (score[0] == best[0] and score[1] > best[1]):
                        best = score

                # Apply best candidate
                best_conf_rank, best_logprob, best_text, best_segments, best_info, best_lang = best
                self.last_confidence, self.last_stats = self._classify_confidence(best_segments, best_text)
                self.last_stats = {**self.last_stats, "audio_seconds": audio_seconds, "pass": "auto_lang_disambiguated", "lang": best_lang}
                text, segments, info = best_text, best_segments, best_info

            self._maybe_update_sticky_language(info, audio_seconds)

        # Always store detected language for downstream use (conditional grammar, etc.)
        if "lang" not in self.last_stats:
            detected = str(getattr(info, "language", "") or "").lower()
            self.last_stats["lang"] = detected if detected else None

        return text

    def dump_effective_decode_args(self) -> dict:
        """
        Returns the actual kwargs we will pass to WhisperModel.transcribe for both base/noisy.
        Useful for debugging and for detecting API mismatches.
        """
        return {
            "base": self._validate_and_build_decode_args(noisy=False),
            "noisy": self._validate_and_build_decode_args(noisy=True),
            "compute_type_effective": self._compute_type_effective,
        }

if __name__ == "__main__":
    t = Transcriber()
    # Mock audio
    import numpy as np
    audio = np.zeros(16000*2, dtype=np.float32)
    print(t.transcribe(audio))
