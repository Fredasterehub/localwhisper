from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Log, Button
from textual.containers import Container, Vertical, Horizontal
from textual.binding import Binding
from tui.matrix import MatrixRain
from core.controller import CoreController
from core.settings import manager as settings
import threading
import time

class StatusWidget(Static):
    """Displays the current status (IDLE, LISTENING, etc)."""
    DEFAULT_CSS = """
    StatusWidget {
        width: 100%;
        height: 3;
        content-align: center middle;
        text-style: bold;
        background: $surface;
        color: $text;
        border: solid green;
    }
    """
    def update_status(self, status: str):
        self.update(f"STATUS: {status}")
        if status == "LISTENING":
            self.styles.border = ("solid", "red")
            self.styles.color = "red"
        elif status == "PROCESSING":
            self.styles.border = ("solid", "cyan")
            self.styles.color = "cyan"
        elif status == "SUCCESS":
            self.styles.border = ("solid", "green")
            self.styles.color = "green"
        else:
            self.styles.border = ("solid", "green")
            self.styles.color = "white"

class WhisperTui(App):
    """Cyberpunk TUI for LocalWhisper."""
    
    CSS = """
    Screen {
        layout: grid;
        grid-size: 2;
        grid-columns: 2fr 1fr;
    }
    
    #left-pane {
        width: 100%;
        height: 100%;
        border: heavy green;
    }
    
    #right-pane {
        width: 100%;
        height: 100%;
        border: heavy green;
    }

    Log {
        background: #050505;
        color: #00ff00;
        max-height: 50%;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("s", "toggle_settings", "Settings"),
    ]

    def __init__(self):
        super().__init__()
        self.matrix = MatrixRain()
        self.status_widget = StatusWidget("STATUS: INITIALIZING...")
        self.log_widget = Log()
        self.controller = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Container(id="left-pane"):
            yield self.matrix
            
        with Vertical(id="right-pane"):
            yield self.status_widget
            yield self.log_widget
            
        yield Footer()

    def on_mount(self):
        self.log_widget.write_line("INITIALIZING SYSTEM...")
        self.log_widget.write_line("CONNECTING TO NEURAL NET...")
        
        # Initialize Controller in a thread to non-block UI
        threading.Thread(target=self._init_controller, daemon=True).start()

    def _init_controller(self):
        try:
            self.controller = CoreController(ui_callback=self.update_state)
            self.matrix.audio_engine = self.controller.audio
            self.controller.start_pipeline()
            self.call_from_thread(self.log_widget.write_line, "SYSTEM ONLINE.")
            self.call_from_thread(self.update_state, "IDLE")
        except Exception as e:
            self.call_from_thread(self.log_widget.write_line, f"CRITICAL ERROR: {e}")

    def update_state(self, state: str):
        self.matrix.set_state(state)
        self.status_widget.update_status(state)
        self.log_widget.write_line(f"[{time.strftime('%H:%M:%S')}] STATE CHANGE: {state}")

    def action_toggle_settings(self):
        self.log_widget.write_line("SETTINGS: To configure, use the GUI version or edit user_settings.json directly.")

    def on_unmount(self):
        if self.controller:
            self.controller.shutdown()

if __name__ == "__main__":
    app = WhisperTui()
    app.run()
