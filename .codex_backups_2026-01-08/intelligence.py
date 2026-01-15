import requests
import config
import json

class IntelligenceEngine:
    def __init__(self):
        self.url = config.OLLAMA_URL
        self.model = config.OLLAMA_MODEL
        print(f"Intelligence Engine connected to {self.model} at {self.url}")
        
    def refine_text(self, text):
        if not text or len(text.strip()) < 2:
            return text

        # System prompt optimized with 2026 best practices
        system_prompt = (
            "You are a minimal grammar correction assistant.\n\n"
            "## TASK\n"
            "Fix ONLY spelling errors and verb conjugation mistakes.\n"
            "Make MINIMAL changes - preserve the user's exact wording, style, and sentence structure.\n\n"

            "## CRITICAL RULES\n"
            "1. Fix spelling mistakes (écrir → écrire, brokan → broken)\n"
            "2. Fix verb conjugations (salute → salue, march → marche)\n"
            "3. Fix obvious typos caused by thick accent (ze → the)\n"
            "4. Remove filler words ONLY: euh, um, ah, like\n"
            "5. PRESERVE the exact same words (do NOT use synonyms)\n"
            "6. PRESERVE the sentence structure (do NOT reorganize)\n"
            "7. PRESERVE punctuation (do NOT add commas/periods unless critical)\n"
            "8. Keep the SAME language (French stays French, English stays English)\n\n"

            "## EXAMPLES\n"
            "Input: 'bonjour le docker il march pas'\n"
            "Output: 'bonjour le docker il marche pas'\n\n"

            "Input: 'je suis en train de t'écrir et cela fonctionne'\n"
            "Output: 'je suis en train de t'écrire et cela fonctionne'\n\n"

            "Input: 'hello ze code is brokan'\n"
            "Output: 'hello the code is broken'\n\n"

            "Input: 'euh je salute mon ami from Montréal'\n"
            "Output: 'je salue mon ami from Montréal'\n\n"

            "## OUTPUT FORMAT\n"
            "Return ONLY the corrected text. No explanations, no quotes, no comments."
        )

        payload = {
            "model": config.OLLAMA_MODEL,
            "prompt": f"{system_prompt}\nInput: '{text}'\nOutput:",
            "stream": False,
            "options": {
                "temperature": 0.0 # STRICT. No creativity. Deterministic.
            }
        }

        try:
            response = requests.post(self.url, json=payload)
            response.raise_for_status()
            result = response.json()
            corrected = result.get("response", "").strip()
            # Remove any wrapping quotes if mistakenly added by LLM
            if corrected.startswith('"') and corrected.endswith('"'):
                corrected = corrected[1:-1]
            return corrected
        except Exception as e:
            print(f"Ollama Error: {e}")
            return text # Fallback to original

if __name__ == "__main__":
    eng = IntelligenceEngine()
    print(eng.refine_text("hello ze python script is broken"))
