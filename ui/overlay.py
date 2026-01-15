import sys
import random
import math
import os
import time
from PyQt6.QtWidgets import QApplication, QWidget, QMenu
from PyQt6.QtCore import Qt, QTimer, QPoint, QRect
from PyQt6.QtGui import QPainter, QColor, QFont, QAction, QCursor, QImage, QPen, QPainterPath
from core.settings import manager as settings

class OverlayBaseWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.state = "IDLE"
        self.locked = True
        self.drag_pos = None

        # Window Flags: Frameless, On Top, Tool
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Eco Mode State
        self.last_activity_time = time.time()
        self._eco_mode = False

    def check_eco_mode(self):
        # Called by subclass animate()
        if self.state == "IDLE" and not self._eco_mode:
            timeout = settings.get("eco_mode_timeout_s") or 60
            if (time.time() - self.last_activity_time) > timeout:
                self._eco_mode = True
                if hasattr(self, 'timer'):
                    self.timer.setInterval(1000) # 1 FPS

    def _wake_from_eco(self):
        if self._eco_mode:
            self._eco_mode = False
            # Restore ~30 FPS
            if hasattr(self, 'timer'):
                self.timer.setInterval(33)

    def set_state(self, state):
        self.state = state
        if state != "IDLE":
             self._wake_from_eco()
        self.last_activity_time = time.time()
        self.update()

    # --- Mouse Interaction ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if not self.locked:
                self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self.locked and self.drag_pos:
            self.move(event.globalPosition().toPoint() - self.drag_pos)

    def contextMenuEvent(self, event):
        menu = QMenu(self)

        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings)
        menu.addAction(settings_action)

        lock_action = QAction("Lock Position" if not self.locked else "Unlock Position", self)
        lock_action.triggered.connect(self.toggle_lock)
        menu.addAction(lock_action)

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(quit_action)

        menu.exec(event.globalPos())

    def open_settings(self):
        if hasattr(self, "on_settings_click"):
            self.on_settings_click()

    def toggle_lock(self):
        self.locked = not self.locked
        self.update()


class MatrixRainWidget(OverlayBaseWidget):
    def __init__(self):
        super().__init__()
        
        # Geometry: Start Bottom Right
        screen = QApplication.primaryScreen().geometry()
        
        self.width_ = 350 # Slightly wider
        self.height_ = 250 # Taller
        
        x = screen.width() - 360
        y = screen.height() - 300
        
        self.setGeometry(x, y, self.width_, self.height_)
        
        self._wave_phase = 0.0
        
        # Matrix Rain Config
        self.font_size = 12
        self.cols = int(self.width_ / self.font_size)
        
        # Authentic Matrix: Half-width Katakana + Latin + Numbers
        # 0xFF61 to 0xFF9F are Half-width Katakana
        self.chars = [chr(i) for i in range(0xFF61, 0xFF9F)] + \
                     list("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789:<>*+-=")
        
        # Drops: List of dicts {col, y, speed, len, head_char}
        self.drops = []
        
        # Initialize with some drops so it's not empty start
        for _ in range(self.cols * 3):
            self._spawn_drop(random_y=True)

        # Animation
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(40)  # 25 fps
        
        self.show()

    def _spawn_drop(self, random_y=False):
        col = random.randint(0, self.cols - 1)
        speed = random.uniform(0.5, 2.0)
        length = random.randint(10, 25) # Longer trails
        
        y = -length * self.font_size
        if random_y:
            y = random.randint(-100, self.height_)
            
        self.drops.append({
            'col': col,
            'y': float(y),
            'speed': speed,
            'len': length,
            'chars': [random.choice(self.chars) for _ in range(length)] # Pre-generate chars for stability
        })

    def animate(self):
        state_speed_mult = 1.0
        if self.state == "LISTENING": state_speed_mult = 2.5
        elif self.state == "PROCESSING": state_speed_mult = 1.5
        
        # Update drops
        active_drops = []
        for d in self.drops:
            d['y'] += d['speed'] * self.font_size * 0.4 * state_speed_mult
            
            # Chance to glitch a character
            if random.random() < 0.05:
                idx = random.randint(0, len(d['chars'])-1)
                d['chars'][idx] = random.choice(self.chars)
            
            # Keep if valid
            if d['y'] - (d['len'] * self.font_size) < self.height_:
                active_drops.append(d)
        
        self.drops = active_drops
        
        # Replenish
        # Target density: approx 3-4 drops per column on average across the whole screen? 
        # width * height / char_area ...
        # Simple heuristic: keep total drops count high
        target_count = self.cols * 3
        if len(self.drops) < target_count:
             for _ in range(target_count - len(self.drops)):
                 if random.random() < 0.3: # Don't spawn all at once
                    self._spawn_drop()

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setFont(QFont("MS Gothic", self.font_size, QFont.Weight.Bold))
        
        # Background
        bg_alpha = 40 if self.state == "IDLE" else 150
        if not self.locked: bg_alpha = 100 
        painter.fillRect(self.rect(), QColor(0, 0, 0, bg_alpha))
        
        if not self.locked:
            painter.setPen(QColor(255, 255, 0))
            painter.drawRect(0, 0, self.width()-1, self.height()-1)

        # Draw Drops
        for d in self.drops:
            col_x = d['col'] * self.font_size
            head_y = d['y']
            
            # Draw trail
            for i in range(d['len']):
                char_y = head_y - (i * self.font_size)
                if char_y > self.height_ + self.font_size: continue
                if char_y < -self.font_size: continue
                
                char = d['chars'][i]
                alpha = 255 - int((i / d['len']) * 255)
                alpha = max(alpha, 0)
                
                # Dim trails if listening to emphasize wave
                if self.state == "LISTENING": alpha = int(alpha * 0.3)
                
                if i == 0: # Head
                    painter.setPen(QColor(220, 255, 220, 255) if self.state != "PROCESSING" else QColor(200, 200, 255))
                else:
                    # Color Logic
                    if self.state == "PROCESSING":
                         c = QColor(0, 100, 255) # Blue Hacking
                    elif self.state == "LISTENING":
                         c = QColor(0, 255, 70) # Keep Green but dimmed
                    else:
                         c = QColor(0, 255, 70) # Standard Matrix
                    
                    painter.setPen(QColor(c.red(), c.green(), c.blue(), alpha))
                
                painter.drawText(col_x, int(char_y), char)

        # Electric Sound Wave (Listening Mode)
        if self.state == "LISTENING" and hasattr(self, 'audio_engine'):
             amp = getattr(self.audio_engine, 'current_amplitude', 0.0)
             
             # Draw "Electric" Wave
             painter.setPen(QPen(QColor(50, 255, 100), 2))
             path = QPainterPath()
             
             cy = self.height_ / 2
             points = 100
             step_x = self.width_ / points
             
             path.moveTo(0, cy)
             for i in range(points + 1):
                 x = i * step_x
                 
                 # Combine sine waves + noise for "electric" feel
                 # amp modulates height
                 noise = random.uniform(-1, 1) * 0.2
                 wave = math.sin(i * 0.2 + self._wave_phase) 
                 
                 # Taper edges
                 taper = 1.0 - abs((i - points/2) / (points/2)) 
                 
                 # Final Y offset
                 dy = (wave + noise) * amp * 100 * taper
                 path.lineTo(x, cy + dy)
             
             painter.drawPath(path)
             
             # Glow effect (draw again wider/transparent)
             painter.setPen(QPen(QColor(50, 255, 100, 100), 6))
             painter.drawPath(path)


class DotWidget(OverlayBaseWidget):
    def __init__(self):
        super().__init__()
        
        # Load Asset
        asset_path = os.path.join(os.path.dirname(__file__), "assets", "dot_orb.png")
        if os.path.exists(asset_path):
             self.orb_pixmap = QImage(asset_path)
        else:
             self.orb_pixmap = None

        screen = QApplication.primaryScreen().geometry()
        self.width_ = 200
        self.height_ = 200
        
        # Position: Top Center
        x = (screen.width() - self.width_) // 2
        y = 50
        self.setGeometry(x, y, self.width_, self.height_)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(33)
        
        self.show()
        
        self._rotation = 0.0
        self._scale_phase = 0.0

    def animate(self):
        self.check_eco_mode()
        self._rotation += 0.5
        self._scale_phase += 0.1
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        
        w, h = self.width_, self.height_
        cx, cy = w // 2, h // 2
        
        if not self.orb_pixmap:
             painter.setPen(QColor(255, 0, 0))
             painter.drawText(10, 50, "ASSET MISSING")
             return

        # Breathing scale
        base_s = 0.8
        pulse = 0.02 * math.sin(self._scale_phase)
        if self.state == "LISTENING":
             base_s = 0.9
             pulse = 0.05 * math.sin(self._scale_phase * 2) # Fast breath
        elif self.state == "PROCESSING":
             base_s = 0.8
             pulse = 0.0
        
        s = base_s + pulse
        
        # Draw Center Orb (Rotating slowly or static?)
        # Let's rotate the orb itself slowly for "floating" effect
        painter.save()
        painter.translate(cx, cy)
        
        if self.state == "PROCESSING":
             painter.rotate(self._rotation * 4) # Fast spin
        else:
             painter.rotate(math.sin(self._scale_phase * 0.5) * 5) # Gentle rock
             
        # Scale
        painter.scale(s, s)
        
        rect_s = 160
        painter.drawImage(QRect(-rect_s//2, -rect_s//2, rect_s, rect_s), self.orb_pixmap)
        painter.restore()
        
        # Colored Glow Overlay
        # Simple radial gradient on top to tint it based on state
        c_tint = QColor(0, 255, 255) # Cyan Idle
        if self.state == "LISTENING": c_tint = QColor(255, 0, 100) # Pink/Red
        elif self.state == "PROCESSING": c_tint = QColor(100, 50, 255) # Purple
        elif self.state == "SUCCESS": c_tint = QColor(0, 255, 50) # Green
        
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Outer Glow
        radius = int(w * 0.6)
        from PyQt6.QtGui import QRadialGradient
        grad = QRadialGradient(cx, cy, radius)
        grad.setColorAt(0.0, QColor(c_tint.red(), c_tint.green(), c_tint.blue(), 0))
        grad.setColorAt(0.7, QColor(c_tint.red(), c_tint.green(), c_tint.blue(), 100))
        grad.setColorAt(1.0, QColor(c_tint.red(), c_tint.green(), c_tint.blue(), 0))
        
        painter.setBrush(grad)
        painter.drawEllipse(0, 0, w, h)
        
        if not self.locked:
            painter.setPen(QColor(255, 255, 0, 200))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(0, 0, self.width()-1, self.height()-1)


class SauronEyeWidget(OverlayBaseWidget):
    def __init__(self):
        super().__init__()
        
        # Load Asset
        asset_path = os.path.join(os.path.dirname(__file__), "assets", "sauron_eye.png")
        if not os.path.exists(asset_path):
             print(f"ERROR: Sauron Asset not found at {asset_path}")
             self.eye_pixmap = None
        else:
             self.eye_pixmap = QImage(asset_path)

        screen = QApplication.primaryScreen().geometry()
        self.width_ = 280
        self.height_ = 280 # Square for circular mask
        x = screen.width() - 320
        y = screen.height() - 320
        self.setGeometry(x, y, self.width_, self.height_)

        self._phase = 0.0
        
        # Pupil/Eye Movement
        self._eye_x = 0.0
        self._eye_y = 0.0
        self._target_x = 0.0
        self._target_y = 0.0
        self._next_saccade = 0
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(33) # 30 FPS

        self.show()

    def animate(self):
        self.check_eco_mode()
        
        self._phase += 0.05
        
        # Movement Logic
        import time
        now = time.time()
        
        if self.state == "IDLE":
             # Random Saccades
             if now > self._next_saccade:
                 self._target_x = random.uniform(-20, 20)
                 self._target_y = random.uniform(-10, 10)
                 self._next_saccade = now + random.uniform(0.5, 4.0)
        elif self.state == "LISTENING":
             # Focus center, intense jitter
             self._target_x = random.uniform(-2, 2)
             self._target_y = random.uniform(-2, 2)
        else: # PROCESSING / SUCCESS
             self._target_x = 0
             self._target_y = 0
             
        # Smooth Interpolation
        self._eye_x += (self._target_x - self._eye_x) * 0.1
        self._eye_y += (self._target_y - self._eye_y) * 0.1
        
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        
        w, h = self.width_, self.height_
        cx, cy = w // 2, h // 2
        
        if not self.eye_pixmap:
            painter.setPen(QColor(255, 0, 0))
            painter.drawText(10, 50, "ASSET MISSING")
            return

        # 1. Circular Mask Container
        # We want the eye to "look around" inside this circle.
        # We do this by setting a clip region.
        path = QPainterPath() 
        # Actually simplest in purely painter:
        path.addEllipse(10, 10, w-20, h-20)
        painter.setClipPath(path)
        
        # 2. Draw Eye Image (Scaled & Translated)
        # Base scale to fill the circle + extra for movement
        base_scale = 1.2
        if self.state == "LISTENING": base_scale = 1.3 # Zoom in
        
        # Pulse scale
        pulse = 1.0 + 0.05 * math.sin(self._phase * 2)
        final_scale = base_scale * pulse
        
        img_w = int(w * final_scale)
        img_h = int(h * final_scale)
        
        # Center of image aligns with Center of widget + Offset
        ix = cx - (img_w // 2) + self._eye_x
        iy = cy - (img_h // 2) + self._eye_y
        
        # State Filters
        if self.state == "IDLE":
             # Dimmer
             painter.setOpacity(0.8)
        elif self.state == "LISTENING":
             painter.setOpacity(1.0)
             # Red tint overlay handled maybe? Or just rely on the image's fire.
        elif self.state == "PROCESSING":
             painter.setOpacity(0.9)
             
        painter.drawImage(QRect(int(ix), int(iy), img_w, img_h), self.eye_pixmap)
        
        # 3. Overlays (On top of eye, still clipped)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # Vignette / Inner Shadow to hide hard edges of image if it moves too far
        # Radial gradient from transparent center to black edge
        from PyQt6.QtGui import QRadialGradient
        grad = QRadialGradient(cx, cy, w//2)
        grad.setColorAt(0.7, QColor(0, 0, 0, 0))
        grad.setColorAt(1.0, QColor(0, 0, 0, 255))
        painter.setBrush(grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(0, 0, w, h)
        
        # Active State Tint
        if self.state == "LISTENING":
             painter.setBrush(QColor(255, 50, 0, 60)) # Red tint
             painter.drawRect(0, 0, w, h)
        elif self.state == "PROCESSING":
             painter.setBrush(QColor(255, 200, 50, 40)) # Orange tint
             painter.drawRect(0, 0, w, h)

        painter.setClipping(False) # Reset clipping
        
        # 4. Rings / UI Elements (Outside the eye ball)
        if self.state == "PROCESSING":
             # Spinning Ring
             painter.setPen(QPen(QColor(255, 200, 0, 150), 3))
             painter.setBrush(Qt.BrushStyle.NoBrush)
             start = int(self._phase * 100)
             painter.drawArc(5, 5, w-10, h-10, start * 16, 120 * 16)
             painter.drawArc(5, 5, w-10, h-10, (start+180) * 16, 120 * 16)

        # Unlock outline
        if not self.locked:
            painter.setPen(QColor(255, 255, 0, 200))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(0, 0, w-1, h-1)



class ModernHUDWidget(OverlayBaseWidget):
    def __init__(self):
        super().__init__()
        
        asset_path = os.path.join(os.path.dirname(__file__), "assets", "hud_ring.png")
        if os.path.exists(asset_path):
             self.hud_pixmap = QImage(asset_path)
        else:
             self.hud_pixmap = None
             
        screen = QApplication.primaryScreen().geometry()
        self.width_ = 300
        self.height_ = 300
        x = screen.width() - 320
        y = 50 
        self.setGeometry(x, y, self.width_, self.height_)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(33)
        
        self._rot = 0.0
        self.show()
        
    def animate(self):
        self.check_eco_mode()
        # Rotation speed based on state
        speed = 0.2
        if self.state == "LISTENING": speed = 0.5
        elif self.state == "PROCESSING": speed = 2.0
        
        self._rot += speed
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        
        w, h = self.width_, self.height_
        cx, cy = w // 2, h // 2
        
        if not self.hud_pixmap:
             painter.drawText(10, 50, "ASSET MISSING")
             return

        # 1. Main Ring (Rotates)
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self._rot)
        
        img_s = 280
        # If State is LISTENING, maybe zoom slightly?
        if self.state == "LISTENING":
            s = 1.0 + 0.05 * math.sin(self._rot * 0.5)
            painter.scale(s, s)
            
        painter.drawImage(QRect(-img_s//2, -img_s//2, img_s, img_s), self.hud_pixmap)
        painter.restore()
        
        # 2. Text Status Center
        painter.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
        painter.setPen(QColor(255, 255, 255, 200))
        
        text = self.state
        if self.state == "IDLE": text = "SYSTEM READY"
        
        # Center text
        fm = painter.fontMetrics()
        tw = fm.horizontalAdvance(text)
        painter.drawText(int(cx - tw//2), int(cy + 5), text)
        
        # 3. Color Overlay for State Change (using Screen/Overlay blend)
        if self.state != "IDLE":
             c = QColor(0, 0, 0)
             if self.state == "LISTENING": c = QColor(255, 50, 50, 100)
             elif self.state == "PROCESSING": c = QColor(255, 200, 0, 80)
             elif self.state == "SUCCESS": c = QColor(50, 255, 50, 100)
             
             # Simple overlay works for tinting.
             painter.setBrush(c)
             painter.setPen(Qt.PenStyle.NoPen)
             painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Overlay)
             painter.drawEllipse(10, 10, w-20, h-20)
             
        if not self.locked:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.setPen(QColor(255, 255, 0, 200))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(0, 0, self.width()-1, self.height()-1)


class CyborgWidget(OverlayBaseWidget):
    def __init__(self):
        super().__init__()
        
        asset_path = os.path.join(os.path.dirname(__file__), "assets", "terminator_skull.png")
        if os.path.exists(asset_path):
             self.skull_pixmap = QImage(asset_path)
        else:
             self.skull_pixmap = None
             
        screen = QApplication.primaryScreen().geometry()
        self.width_ = 280
        self.height_ = 350 # Taller for skull
        x = screen.width() - 320
        y = screen.height() - 400
        self.setGeometry(x, y, self.width_, self.height_)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(33)
        
        self._glow_phase = 0.0
        self.show()

    def animate(self):
        self.check_eco_mode()
        self._glow_phase += 0.2
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        
        w, h = self.width_, self.height_
        cx, cy = w // 2, h // 2
        
        if not self.skull_pixmap:
             painter.drawText(10, 50, "ASSET MISSING")
             return

        # 1. Draw Skull Asset
        # Fit to width, maintain aspect ratio
        img_w = 260
        img_h = 320 # Approx
        
        painter.drawImage(QRect(int(cx - img_w//2), int(cy - img_h//2), img_w, img_h), self.skull_pixmap)
        
        # 2. Glowing Eye Overlay
        # We know roughly where the eyes are in the asset. 
        # Let's say Left Eye is at 35% W, 40% H and Right Eye at 65% W, 40% H?
        # Based on the image generated "front view".
        # Let's assume standard skull proportions.
        
        left_eye_pos = (int(cx - 45), int(cy - 20))
        right_eye_pos = (int(cx + 45), int(cy - 20))
        
        # Eye Glow Intensity
        base_alpha = 100
        if self.state == "LISTENING": base_alpha = 240
        elif self.state == "PROCESSING": base_alpha = 180
        
        # Pulse
        pulse = 0.5 + 0.5 * math.sin(self._glow_phase)
        alpha = int(base_alpha * (0.8 + 0.2 * pulse))
        
        # Draw Red Glows
        painter.setPen(Qt.PenStyle.NoPen)
        c = QColor(255, 0, 0, alpha)
        
        # Simple radial glow for eyes
        from PyQt6.QtGui import QRadialGradient
        
        def draw_eye_glow(px, py, radius):
            g = QRadialGradient(px, py, radius)
            g.setColorAt(0.0, QColor(255, 50, 50, alpha))
            g.setColorAt(0.4, QColor(255, 0, 0, int(alpha * 0.6)))
            g.setColorAt(1.0, QColor(255, 0, 0, 0))
            painter.setBrush(g)
            painter.drawEllipse(px - radius, py - radius, radius * 2, radius * 2)

        # Draw both eyes
        draw_eye_glow(left_eye_pos[0], left_eye_pos[1], 25)
        draw_eye_glow(right_eye_pos[0], right_eye_pos[1], 25)
        
        # 3. Scanning Bar (Terminator Vision style) if Processing
        if self.state == "PROCESSING":
             bar_y = (math.sin(self._glow_phase * 0.5) + 1) / 2 * h # 0 to h
             painter.setPen(QColor(255, 0, 0, 150))
             painter.drawLine(0, int(bar_y), w, int(bar_y))
             
             # "ANALYZING" text
             painter.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
             painter.setPen(QColor(255, 0, 0, 200))
             painter.drawText(10, int(bar_y) - 5, "ANALYZING...")

        if not self.locked:
            painter.setPen(QColor(255, 255, 0, 200))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(0, 0, self.width()-1, self.height()-1)


def create_overlay_widget(skin: str, audio_engine=None) -> OverlayBaseWidget:
    s = (skin or "").strip().lower()
    w = None
    if s == "dot":
        w = DotWidget()
    elif s == "sauron_eye":
        w = SauronEyeWidget()
    elif s == "surprise":
        w = ModernHUDWidget()
    elif s == "terminator":
        w = CyborgWidget()
    else:
        w = MatrixRainWidget()
    
    if audio_engine:
        w.audio_engine = audio_engine
    return w

def run_overlay(state_queue, on_settings_click=None, app=None, audio_engine=None):
    if app is None:
        app = QApplication(sys.argv)
    
    # CRITICAL FIX: Prevent app from quitting when Settings closes
    app.setQuitOnLastWindowClosed(False)
        
    widget = create_overlay_widget(settings.get("overlay_skin"), audio_engine)
    widget.on_settings_click = on_settings_click
    last_skin = str(settings.get("overlay_skin") or "")
    
    # Check queue for updates
    timer = QTimer()
    def check_queue():
        nonlocal widget, last_skin

        # Hot-swap skins if changed.
        current_skin = str(settings.get("overlay_skin") or "")
        if current_skin != last_skin:
            pos = widget.pos()
            locked = getattr(widget, "locked", True)
            state = getattr(widget, "state", "IDLE")

            try:
                widget.close()
                widget.deleteLater() # Cleanup
            except Exception:
                pass

            widget = create_overlay_widget(current_skin, audio_engine)
            widget.on_settings_click = on_settings_click
            # Try to preserve pos if possible, or reset if size differs wildly?
            # Ideally center it if it was default? For now keep pos.
            widget.move(pos)
            widget.locked = locked
            widget.set_state(state)
            last_skin = current_skin

        # Drain
        state = None
        while not state_queue.empty():
            state = state_queue.get()
        if state is not None:
            widget.set_state(state)
    
    timer.timeout.connect(check_queue)
    timer.start(100)
    
    sys.exit(app.exec())

