import sys
import random
from PyQt6.QtWidgets import QApplication, QWidget, QMenu
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt6.QtGui import QPainter, QColor, QFont, QAction, QCursor

class MatrixRainWidget(QWidget):
    def __init__(self):
        super().__init__()
        # Window Flags: Frameless, On Top, Tool
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Geometry: Start Bottom Right
        screen = QApplication.primaryScreen().geometry()
        print(f"DEBUG: Screen Size: {screen.width()}x{screen.height()}")
        
        self.width_ = 250
        self.height_ = 150
        
        x = screen.width() - 300
        y = screen.height() - 250
        print(f"DEBUG: Widget Pos: {x},{y}")
        
        self.setGeometry(x, y, self.width_, self.height_)
        
        self.state = "IDLE" 
        self.locked = True
        self.drag_pos = None

        # Matrix Rain Config
        self.font_size = 10 # Dense
        self.columns = int(self.width_ / self.font_size)
        self.drops = [1 for _ in range(self.columns)] # Y position of drops
        # Authentic Matrix: Half-width Katakana + Numbers
        self.chars = "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ0123456789:<+*"
        
        # Animation
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(50) 
        
        self.show()

    def set_state(self, state):
        self.state = state
        self.update()

    def animate(self):
        # Update drops
        if self.state in ["IDLE", "LISTENING", "PROCESSING", "SUCCESS"]:
            for i in range(len(self.drops)):
                # Randomize speed based on state
                speed = 1
                if self.state == "LISTENING": speed = 3
                if self.state == "PROCESSING": speed = 2
                
                # Falling logic
                if random.random() > 0.95: # Random start
                    self.drops[i] += speed
                
                # Reset if out of bounds
                if self.drops[i] * self.font_size > self.height_ and random.random() > 0.975:
                    self.drops[i] = 0
                
                self.drops[i] += speed if self.drops[i] > 0 else 0
                
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        # "MS Gothic" for Authentic Matrix Glpyhs
        painter.setFont(QFont("MS Gothic", self.font_size, QFont.Weight.Bold))
        
        # Background
        bg_alpha = 20 if self.state == "IDLE" else 180
        if not self.locked: bg_alpha = 100 
        
        painter.fillRect(self.rect(), QColor(0, 0, 0, bg_alpha))
        
        if not self.locked:
            painter.setPen(QColor(255, 255, 0))
            painter.drawRect(0, 0, self.width()-1, self.height()-1)

        # Draw Matrix Rain with TRIALS
        trail_length = 8 # Length of the tail
        
        for i in range(len(self.drops)):
            x = i * self.font_size
            head_y = self.drops[i] * self.font_size
            
            # Draw Trail
            for j in range(trail_length):
                char_y = head_y - (j * self.font_size)
                if char_y < 0: continue
                
                # Pick Character (Randomize slightly for "glitch" effect)
                text = random.choice(self.chars)
                
                # Color Logic
                alpha = 255 - (j * (255 // trail_length)) # Fade out
                alpha = max(alpha, 30)
                
                if self.state == "IDLE":
                     base_color = QColor(0, 255, 70) 
                elif self.state == "LISTENING":
                     base_color = QColor(255, 50, 50) 
                elif self.state == "PROCESSING":
                     base_color = QColor(50, 150, 255) 
                elif self.state == "SUCCESS":
                     base_color = QColor(255, 255, 255) 
                else:
                     base_color = QColor(0, 255, 70)

                # Head is White/Bright
                if j == 0:
                    painter.setPen(QColor(220, 255, 220, 255))
                else:
                    painter.setPen(QColor(base_color.red(), base_color.green(), base_color.blue(), alpha))
                
                painter.drawText(x, int(char_y), text)

    # --- Mouse Interaction ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if not self.locked:
                self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            else:
                # pass click through? (Difficult in PyQt without extensive Win32 API)
                pass
        
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
        # We need to signal the main thread or pass the engine
        # Since this runs in the UI process, we can emit a signal or call a callback if passed.
        # Ideally, main.py should pass a callback.
        if hasattr(self, 'on_settings_click'):
            self.on_settings_click()

    def toggle_lock(self):
        self.locked = not self.locked
        self.update()

def run_overlay(state_queue, on_settings_click=None, app=None):
    if app is None:
        app = QApplication(sys.argv)
    
    # CRITICAL FIX: Prevent app from quitting when Settings closes
    # (MatrixWindow produces 'Qt.Tool' flag which is ignored by default quit logic)
    app.setQuitOnLastWindowClosed(False)
        
    widget = MatrixRainWidget()
    widget.on_settings_click = on_settings_click
    
    # Check queue for updates
    timer = QTimer()
    def check_queue():
        if not state_queue.empty():
            state = state_queue.get()
            widget.set_state(state)
    
    timer.timeout.connect(check_queue)
    timer.start(100)
    
    sys.exit(app.exec())
