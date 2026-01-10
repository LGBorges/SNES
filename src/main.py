# src/main.py
import os, sys, faulthandler
from PySide6.QtWidgets import QApplication
from app.paths import app_base_dir, save_dir
from app.logging_conf import setup_logger
from app.gui import MainWindow

def run_gui():
    _stream = sys.stderr or getattr(sys, "__stderr__", None)
    try:
        if _stream: faulthandler.enable(_stream)
    except Exception:
        pass
    try: os.chdir(app_base_dir())
    except Exception: pass

    logger = setup_logger(save_dir())
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    win = MainWindow(logger); win.showFullScreen()
    rc = app.exec(); sys.exit(rc)

if __name__ == "__main__":
    run_gui()
