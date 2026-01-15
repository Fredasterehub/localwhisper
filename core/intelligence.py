import re
import requests

import config
from core.logger import log
from core.settings import manager as settings


class IntelligenceEngine:
    def __init__(self):
        self.url = config.OLLAMA_URL
        self.model = config.OLLAMA_MODEL
        # Use Session for connection reuse (massive speedup on Windows)
        self._session = requests.Session()
        print(f"Intelligence Engine connected to {self.model} at {self.url}")

    @staticmethod
    def _is_code_like(text: str) -> bool:
        t = text.strip()
        if not t:
            return True

        # Multi-line output is overwhelmingly terminal output / code / logs.
        if "\n" in t or "\r" in t:
            return True

        # High-signal CLI/code markers.
        code_markers = [
            " --",
            "--",
            " -",
            " /",
            "\\",
            "/",
            "::",
            "://",
            "@",
            "$",
            "|",
            "&&",
            "||",
            ";",
            ">>",
            "<<",
            "{",
            "}",
            "[",
            "]",
            "(",
            ")",
            "<",
            ">",
            "=>",
            "==",
            "!=",
            ":\\",
            "~/",
            "#",
            "`",
        ]
        if any(m in t for m in code_markers):
            return True

        if re.search(r"\b([A-Za-z]:\\|/home/|/usr/|/etc/|~\/)\b", t):
            return True
        if re.search(r"(^|\s)--?[A-Za-z0-9][A-Za-z0-9_-]*", t):
            return True
        if re.search(r"\b(sudo|ssh|scp|rsync|tmux|vim|nvim|nano|git|pip|conda|docker|kubectl|helm)\b", t):
            return True
        if re.search(r"(^|\s)[A-Za-z_][A-Za-z0-9_]*=", t):
            return True

        # High symbol density => likely technical.
        symbol_count = sum(1 for ch in t if not (ch.isalpha() or ch.isspace()))
        if symbol_count / max(1, len(t)) >= 0.18:
            return True

        return False

    def _should_refine(self, text: str) -> bool:
        if not text or len(text.strip()) < 2:
            return False
        if len(text) > int(settings.get("llm_refine_max_chars")):
            return False
        if settings.get("llm_refine_skip_code_like") and self._is_code_like(text):
            return False
        return True

    def refine_text(self, text: str) -> str:
        if not self._should_refine(text):
            return text

        prompt = (
            "You are a STRICT copy editor for dictated prose.\n"
            "Return ONLY the corrected text. No quotes, no explanations.\n\n"
            "Rules:\n"
            "1) Preserve meaning exactly. Do NOT paraphrase.\n"
            "2) Do NOT translate or change language.\n"
            "3) Fix only: obvious spelling, obvious homophone mistakes, basic punctuation, capitalization.\n"
            "4) Remove only these fillers when standalone words: euh, um, uh, ah, like.\n"
            "5) Preserve whitespace (including leading/trailing spaces).\n"
            "6) If unsure, output the input unchanged.\n\n"
            "Input:\n"
            "<<<\n"
            f"{text}\n"
            ">>>\n"
            "Corrected:\n"
        )

        payload = {
            "model": config.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.0,
            },
        }

        try:
            response = self._session.post(
                self.url,
                json=payload,
                timeout=float(settings.get("ollama_timeout_s")),
            )
            response.raise_for_status()
            result = response.json()
            corrected = (result.get("response", "") or "").strip()

            if corrected.startswith('"') and corrected.endswith('"'):
                corrected = corrected[1:-1]

            if not corrected:
                return text

            # Safety: if the model output diverges wildly, skip refinement.
            if abs(len(corrected) - len(text)) > max(80, int(len(text) * 0.6)):
                log("LLM output length diverged; skipping refinement.", "warning")
                return text

            # Safety: preserve any CLI-ish "critical tokens" if present.
            critical = re.findall(r"(--?[A-Za-z0-9][A-Za-z0-9_-]*|[A-Za-z]:\\\\[^\\s]+|/[^\\s]+)", text)
            for token in critical:
                if token and token not in corrected:
                    log("LLM output dropped a critical token; skipping refinement.", "warning")
                    return text

            # Safety: avoid accidental language "translation" (FR <-> EN) on short utterances.
            def guess_lang_en_fr(s: str) -> str | None:
                s2 = re.sub(r"[^A-Za-zÀ-ÿ\\s']", " ", s.lower())
                words = [w for w in s2.split() if w]
                if len(words) < 4:
                    return None
                fr = {"je", "tu", "il", "elle", "on", "nous", "vous", "ils", "elles", "de", "des", "du", "la", "le", "les", "un", "une", "et", "est", "pas", "pour", "avec", "sur", "dans", "que", "qui", "ce", "ça"}
                en = {"i", "you", "he", "she", "we", "they", "the", "a", "an", "and", "is", "are", "not", "for", "with", "on", "in", "to", "that", "this", "it", "of"}
                fr_hits = sum(1 for w in words if w in fr)
                en_hits = sum(1 for w in words if w in en)
                if fr_hits >= en_hits + 3:
                    return "fr"
                if en_hits >= fr_hits + 3:
                    return "en"
                return None

            in_lang = guess_lang_en_fr(text)
            out_lang = guess_lang_en_fr(corrected)
            if in_lang and out_lang and in_lang != out_lang:
                log("LLM output appears translated; skipping refinement.", "warning")
                return text

            return corrected
        except Exception as e:
            log(f"Ollama Error: {e}", "warning")
            return text


if __name__ == "__main__":
    eng = IntelligenceEngine()
    print(eng.refine_text("hello ze python script is broken"))
