import json
import os
import config

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
            "setup_completed": False
        }
        self.settings = self.load_settings()

    def load_settings(self):
        if not os.path.exists(self.settings_path):
            return self.defaults.copy()
        
        try:
            with open(self.settings_path, 'r') as f:
                data = json.load(f)
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
        self.settings[key] = value
        self.save_settings()

# Global singleton
manager = SettingsManager()
