import os
from PySide6.QtGui import QPixmap
from .paths import package_data_dir, app_base_dir
def load_background() -> QPixmap | None:
    for base in (package_data_dir(), app_base_dir()):
        p = os.path.join(base, "snes_bg.png")
        if os.path.exists(p):
            try: return QPixmap(p)
            except Exception: pass
    return None
