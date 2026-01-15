"""
Manual, unit-ish diagnostics helpers.

Run:
  venv\\Scripts\\python -m core.diagnostics
"""

import json
from core.logger import log
from core.settings import manager as settings
from core.transcriber import Transcriber


def print_effective_decode_params():
    t = Transcriber()
    effective = t.dump_effective_decode_args()
    print("=== Effective faster-whisper transcribe kwargs ===")
    print(json.dumps(effective, indent=2))

    # Also print current confidence thresholds.
    print("\n=== Confidence thresholds ===")
    keys = [
        "reject_no_speech_prob",
        "reject_avg_logprob",
        "reject_min_chars",
        "conf_high_min_avg_logprob",
        "conf_high_max_avg_no_speech_prob",
        "conf_high_max_avg_compression_ratio",
        "conf_med_min_avg_logprob",
        "conf_med_max_avg_no_speech_prob",
        "conf_med_max_avg_compression_ratio",
    ]
    print(json.dumps({k: settings.get(k) for k in keys}, indent=2))


def main():
    try:
        print_effective_decode_params()
    except Exception as e:
        log(f"Diagnostics failed: {e}", "error")
        raise


if __name__ == "__main__":
    main()

