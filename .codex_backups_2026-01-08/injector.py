import time
import sys
import pyperclip
from pynput.keyboard import Controller, Key

class Injector:
    def __init__(self):
        self.keyboard = Controller()

    def type_text(self, text):
        """
        Inject text into active window.
        SAFE MODE: Uses Clipboard for long text, but RESTORES previous clipboard.
        """
        if not text:
            return

        print(f"Injecting: {text}")
        
        # --- HYBRID MODE ---
        if len(text) > 60:
            try:
                # 1. Save current clipboard
                old_clipboard = pyperclip.paste()
                
                # 2. Inject new text via clipboard
                pyperclip.copy(text)
                time.sleep(0.05) # Wait for OS
                
                with self.keyboard.pressed(Key.ctrl):
                    self.keyboard.type('v')
                    
                # 3. Restore old clipboard
                # Wait for paste to consume the buffer (important!)
                time.sleep(0.2) 
                pyperclip.copy(old_clipboard)
                
                return
            except Exception as e:
                print(f"Clipboard Injection Failed: {e}")
                pass # Fallback to typing

        # Typing Mode (Short text or fallback)
        try:
            for char in text:
                self.keyboard.type(char)
                time.sleep(0.005) 
        except Exception as e:
            print(f"Injection Failed: {e}")

if __name__ == "__main__":
    time.sleep(2)
    inj = Injector()
    inj.type_text("Short text types.")
