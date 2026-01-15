from textual.widget import Widget
from rich.text import Text
from rich.color import Color
import random
import time

class MatrixRain(Widget):
    """
    A Matrix Rain widget for Textual.
    Renders falling characters with trails using Rich.
    """
    
    DEFAULT_CSS = """
    MatrixRain {
        width: 100%;
        height: 100%;
        background: #000000;
        min-height: 20;
    }
    """

    def __init__(self, name=None):
        super().__init__(name=name)
        # 0xFF61 to 0xFF9F are Half-width Katakana
        self.chars = [chr(i) for i in range(0xFF61, 0xFF9F)] + \
                     list("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789:<>*+-=")
        self.messages = ["WAKE UP", "SYSTEM", "CONNECTED", "LOCALWHISPER", "MATRIX", "FOLLOW", "RABBIT", "KNOCK", "NEO", "TRINITY"]
        self.drops = []
        self.last_update = time.time()
        self.state = "IDLE"

    def on_mount(self):
        self.set_interval(0.05, self.update_rain)

    def set_state(self, state):
        self.state = state
        self.refresh()

    def update_rain(self):
        w, h = self.size
        if w == 0 or h == 0: return

        # Initialize drops if needed
        cols = w
        # High Density: > 100% coverage
        target_drops = int(cols * 1.5)
        
        # Spawn new drops
        if len(self.drops) < target_drops:
             # Spawn multiple if needed (aggressive)
             for _ in range(5):
                 if random.random() < 0.6:
                    col = random.randint(0, cols - 1)
                    speed = random.uniform(0.5, 1.5)
                    length = random.randint(5, 20)
                    
                    # Message Injection
                    chars = []
                    is_msg = False
                    if random.random() < 0.05:
                        is_msg = True
                        msg = random.choice(self.messages)
                        full = ""
                        while len(full) < length: full += msg
                        chars = list(full[:length])
                    else:
                        chars = [random.choice(self.chars) for _ in range(length)]
                        
                    self.drops.append({
                        'col': col,
                        'y': float(-length),
                        'speed': speed,
                        'len': length,
                        'chars': chars,
                        'is_msg': is_msg
                    })

        # Update positions
        active_drops = []
        speed_mult = 1.0
        if self.state == "LISTENING": speed_mult = 2.5
        elif self.state == "PROCESSING": speed_mult = 0.5

        for d in self.drops:
            d['y'] += d['speed'] * speed_mult
            
            # Glitch
            if random.random() < 0.05:
                idx = random.randint(0, len(d['chars'])-1)
                d['chars'][idx] = random.choice(self.chars)
                
            if d['y'] - d['len'] < h:
                active_drops.append(d)
        
        self.drops = active_drops
        self.refresh()

    def render(self):
        w, h = self.size
        canvas = [[" " for _ in range(w)] for _ in range(h)]
        colors = [[None for _ in range(w)] for _ in range(h)]
        
        # Base color
        if self.state == "IDLE": base_color = (0, 255, 70)
        elif self.state == "LISTENING": base_color = (0, 100, 30) # Dimmed Green
        elif self.state == "PROCESSING": base_color = (0, 100, 255) # Blue
        elif self.state == "SUCCESS": base_color = (255, 255, 255) # White
        else: base_color = (0, 255, 70)

        for d in self.drops:
            col = d['col']
            if col >= w: continue
            
            head_y = int(d['y'])
            
            for i in range(d['len']):
                char_y = head_y - i
                if 0 <= char_y < h:
                    char = d['chars'][i]
                    canvas[char_y][col] = char
                    
                    # Fade
                    params = d['len']
                    if params == 0: params = 1
                    alpha = 1.0 - (i / params)
                    if alpha < 0: alpha = 0
                    
                    if i == 0 or d.get('is_msg'): # Head or Message
                         if d.get('is_msg'):
                             colors[char_y][col] = (255, 255, 255)
                         else:
                             colors[char_y][col] = (200, 255, 200) # Bright
                    else:
                         r = int(base_color[0] * alpha)
                         g = int(base_color[1] * alpha)
                         b = int(base_color[2] * alpha)
                         colors[char_y][col] = (r, g, b)

        if self.state == "LISTENING" and hasattr(self, 'audio_engine'):
             amp = getattr(self.audio_engine, 'current_amplitude', 0.0)
             
             # Audio Reactive Bar
             # Center row
             cy = h // 2
             
             # Block chars:  ▂▃▅▇
             bar_chars = " ▂▃▅▇"
             
             for x in range(w):
                 # Sine + Noise
                 noise = random.uniform(0, 1)
                 # Visualize stereo-like symmetry from center
                 dx = abs(x - w // 2) / (w // 2)
                 val = (amp * (1.0 - dx) * 2.0) + (noise * 0.2)
                 
                 val = max(0.0, min(1.0, val))
                 
                 idx = int(val * (len(bar_chars) - 1))
                 char = bar_chars[idx]
                 
                 # Draw in center row
                 if 0 <= cy < h:
                     # Overwrite matrix rain
                     canvas[cy][x] = char
                     colors[cy][x] = (50, 255, 50) # Bright Green
                     
                     # Add glowing neighbors
                     if val > 0.5:
                         if cy-1 >= 0: canvas[cy-1][x] = char
                         if cy+1 < h: canvas[cy+1][x] = char
                         colors[cy-1][x] = (0, 150, 0)
                         colors[cy+1][x] = (0, 150, 0)

        # Build Text
        final_text = Text()
        for y in range(h):
            row_text = Text()
            for x in range(w):
                char = canvas[y][x]
                c_val = colors[y][x]
                if c_val:
                    style = f"rgb({c_val[0]},{c_val[1]},{c_val[2]})"
                    row_text.append(char, style=style)
                else:
                    row_text.append(char)
            row_text.append("\n")
            final_text.append(row_text)
            
        return final_text
