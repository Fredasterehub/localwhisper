from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QSlider, 
                             QComboBox, QRadioButton, QButtonGroup, QPushButton, 
                             QHBoxLayout, QProgressBar, QWidget, QCheckBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeyEvent
from core.settings import manager

class KeyBinder(QPushButton):
    def __init__(self, current_key):
        super().__init__()
        self.setText(str(current_key).upper())
        self.current_key = current_key
        self.listening = False
        self.clicked.connect(self.start_listening)
        self.setStyleSheet("background-color: #333; color: white; border: 1px solid #555; padding: 5px;")

    def start_listening(self):
        self.listening = True
        self.setText("PRESS ANY KEY...")
        self.setStyleSheet("background-color: #007acc; color: white; border: 1px solid #0099ff;")

    def keyPressEvent(self, event: QKeyEvent):
        if self.listening:
            key = event.text()
            if not key or key.strip() == "":
                 key = Qt.Key(event.key()).name.lower()
            
            # Normalize
            if "space" in key: key = "space"
            if "control" in key: key = "ctrl"
            if "shift" in key: key = "shift"
            if "alt" in key: key = "alt"
            
            self.current_key = key
            self.setText(str(key).upper())
            self.listening = False
            self.setStyleSheet("background-color: #333; color: white; border: 1px solid #555;")
        else:
            super().keyPressEvent(event)

class SettingsDialog(QDialog):
    def __init__(self, audio_engine):
        super().__init__()
        self.audio_engine = audio_engine
        self.setWindowTitle("Settings")
        self.setFixedWidth(350)
        self.setStyleSheet("""
            QDialog { background-color: #2F3136; color: #dcddde; }
            QLabel { font-weight: bold; margin-top: 10px; }
            QSlider::groove:horizontal { height: 8px; background: #40444b; border-radius: 4px; }
            QSlider::handle:horizontal { background: #007acc; width: 16px; margin: -4px 0; border-radius: 8px; }
            QProgressBar { background: #40444b; border: none; border-radius: 4px; text-align: center; }
            QProgressBar::chunk { background: #43b581; border-radius: 4px; }
            QPushButton { background-color: #5865f2; color: white; border-radius: 4px; padding: 8px; border: none; }
            QPushButton:hover { background-color: #4752c4; }
            QComboBox { background: #202225; padding: 5px; border-radius: 4px; color: white; }
        """)
        
        layout = QVBoxLayout()
        
        # --- Mic/Device ---
        layout.addWidget(QLabel("INPUT DEVICE"))
        self.device_combo = QComboBox()
        self.devices = audio_engine.get_devices()
        current_idx = manager.get("input_device_index")
        for i, dev in enumerate(self.devices):
            if dev['max_input_channels'] > 0:
                self.device_combo.addItem(f"{dev['name']}", userData=i)
                if i == current_idx:
                    self.device_combo.setCurrentIndex(self.device_combo.count() - 1)
        layout.addWidget(self.device_combo)

        layout.addWidget(self.device_combo)

        # --- Language Lock ---
        layout.addWidget(QLabel("FORCE OUTPUT LANGUAGE"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("Auto-Detect", "auto")
        self.lang_combo.addItem("English", "en")
        self.lang_combo.addItem("French", "fr")
        self.lang_combo.addItem("Spanish", "es")
        self.lang_combo.addItem("German", "de")
        self.lang_combo.addItem("Japanese", "ja")
        
        # Set current
        cur_lang = manager.get("transcription_language")
        idx = self.lang_combo.findData(cur_lang)
        if idx >= 0: self.lang_combo.setCurrentIndex(idx)
        else: self.lang_combo.setCurrentIndex(0)
        
        layout.addWidget(self.lang_combo)

        # --- Visualizer ---
        self.meter = QProgressBar()
        self.meter.setRange(0, 100)
        self.meter.setTextVisible(False)
        self.meter.setFixedHeight(10)
        layout.addWidget(self.meter)
        
        # Start Metering (Efficient)
        self.audio_engine.start_metering()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_meter)
        self.timer.start(50)

        # --- VAD Threshold ---
        layout.addWidget(QLabel("INPUT SENSITIVITY"))
        self.thresh_label = QLabel(f"{int(manager.get('vad_threshold')*100)}%")
        self.thresh_label.setStyleSheet("font-weight: normal; margin-top: 0px;")
        layout.addWidget(self.thresh_label)
        
        self.thresh_slider = QSlider(Qt.Orientation.Horizontal)
        self.thresh_slider.setRange(1, 99)
        self.thresh_slider.setValue(int(manager.get("vad_threshold") * 100))
        self.thresh_slider.valueChanged.connect(lambda v: self.thresh_label.setText(f"{v}%"))
        layout.addWidget(self.thresh_slider)

        # --- Mode ---
        layout.addWidget(QLabel("INPUT MODE"))
        self.mode_group = QButtonGroup()
        
        self.rb_voice = QRadioButton("Voice Activity")
        self.rb_ptt = QRadioButton("Push to Talk")
        
        if manager.get("mode") == "push_to_talk":
            self.rb_ptt.setChecked(True)
        else:
            self.rb_voice.setChecked(True)
            
        self.mode_group.addButton(self.rb_voice)
        self.mode_group.addButton(self.rb_ptt)
        
        layout.addWidget(self.rb_voice)
        layout.addWidget(self.rb_ptt)
        
        # --- PTT Key ---
        box_ptt = QHBoxLayout()
        box_ptt.addWidget(QLabel("SHORTCUT:"))
        self.key_bind_btn = KeyBinder(manager.get("push_to_talk_key"))
        box_ptt.addWidget(self.key_bind_btn)
        layout.addLayout(box_ptt)

        # --- AI Toggle ---
        self.cb_intelligence = QCheckBox("Enable AI Grammar (Mistral)")
        self.cb_intelligence.setChecked(manager.get("use_intelligence"))
        self.cb_intelligence.setStyleSheet("margin-top: 10px; font-weight: bold;")
        layout.addWidget(self.cb_intelligence)

        # --- Actions ---
        layout.addSpacing(20)
        save_btn = QPushButton("Done")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
        
        self.setLayout(layout)

    def update_meter(self):
        level = self.audio_engine.get_current_volume()
        val = min(100, int(level * 100))
        self.meter.setValue(val)

    def closeEvent(self, event):
        # Stop metering when closed (X or Done)
        self.audio_engine.stop_metering()
        super().closeEvent(event)

    def save_settings(self):
        try:
            manager.set("vad_threshold", self.thresh_slider.value() / 100.0)
            
            idx = self.device_combo.currentData()
            if idx is not None:
                manager.set("input_device_index", idx)
            
            manager.set("transcription_language", self.lang_combo.currentData())

            if self.rb_ptt.isChecked():
                manager.set("mode", "push_to_talk")
            else:
                manager.set("mode", "voice_activation")
                
            manager.set("push_to_talk_key", self.key_bind_btn.current_key)
            manager.set("use_intelligence", self.cb_intelligence.isChecked())
            manager.set("setup_completed", True)
            
            self.audio_engine.stop_metering() # Ensure stop
                
            self.accept()
        except Exception as e:
            print(f"Settings Save Error: {e}")
            self.accept() # Close anyway to prevent stuck state
