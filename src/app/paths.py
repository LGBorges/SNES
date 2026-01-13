import os, sys, tempfile
def is_frozen() -> bool:
    return getattr(sys, "frozen", False)

def app_base_dir() -> str:
    if is_frozen(): return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def package_data_dir() -> str:
    if is_frozen(): return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))

def save_dir() -> str:
    return os.path.join(app_base_dir(), "Saves")

def rom_root() -> str:
    candidate_pkg = os.path.join(package_data_dir(), "Roms")
    if os.path.isdir(candidate_pkg):
        return candidate_pkg
    return os.path.join(app_base_dir(), "Roms")

def emulator_packaged_path() -> str:
    p = os.path.join(package_data_dir(), "snes9x-x64.exe")
    return p if os.path.exists(p) else os.path.join(app_base_dir(), "snes9x-x64.exe")

def runtime_dir() -> str:
    base = os.environ.get("LOCALAPPDATA", tempfile.gettempdir())
    rd = os.path.join(base, "SNESLauncher", "runtime")
    os.makedirs(rd, exist_ok=True)
    return rd
