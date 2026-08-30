from PySide6.QtWidgets import QApplication
from spot_detector.controller.entry_point import AppStartManager

import multiprocessing as mp
import sys

mp.freeze_support()
app = QApplication()
app.setApplicationName("Spot Detector")
app.setApplicationDisplayName("Spot Detector")
start_manager = AppStartManager()
start_manager.start_from_welcome()
sys.exit(app.exec())
