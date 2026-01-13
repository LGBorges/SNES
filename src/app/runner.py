
import os
import zipfile
import tempfile
import shutil
import subprocess
import hashlib
import re
import errno
import bz2
import lzma
from typing import Optional, Tuple
from PySide6.QtCore import QObject, Signal

from app.paths import emulator_packaged_path, runtime_dir, save_dir

def _sha1(path: str) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def _win_long(p: str) -> str:
    """
    Suporte a caminhos longos (MAX_PATH) no Windows via prefixo \\?\
    Inclui tratamento de UNC. Em outras plataformas, retorna inalterado.
    """
    try:
        if os.name == "nt":
            p = os.path.normpath(p)
            if p.startswith("\\\\"):  # UNC
                if not p.startswith("\\\\?\\UNC\\"):
                    return "\\\\?\\UNC\\" + p[2:]
            elif not p.startswith("\\\\?\\"):
                return "\\\\?\\" + p
        return p
    except Exception:
        return p

def resolve_emulator_exe() -> Tuple[str, str]:
    """
    Copia o emulador para o runtime e retorna (exe_path, emu_dir).
    Se não houver arquivo empacotado, usa o caminho original.
    """
    src = emulator_packaged_path()
    if os.path.exists(src):
        rd = runtime_dir()
        dst = os.path.join(rd, os.path.basename(src))
        try:
            if (not os.path.exists(dst)) or (_sha1(dst) != _sha1(src)):
                shutil.copy2(src, dst)
        except Exception:
            return src, os.path.dirname(src)
        return dst, rd
    return src, os.path.dirname(src)

def _ensure_save_folders(logger) -> str:
    """
    Garante que a pasta de saves persistente exista e retorna seu caminho absoluto.
    Cria também subpastas opcionais para organização.
    """
    base = save_dir()
    try:
        os.makedirs(base, exist_ok=True)
        os.makedirs(os.path.join(base, "SRAM"), exist_ok=True)
        os.makedirs(os.path.join(base, "States"), exist_ok=True)
    except Exception:
        logger.exception("Falha ao criar pastas de save persistentes")
    return base

def _patch_fullscreen_conf(emu_dir: str, width: int, height: int, logger) -> None:
    """
    Atualiza snes9x.conf ao lado do executável (no runtime):
    - Stretch:Enabled = TRUE
    - Stretch:MaintainAspectRatio = FALSE
    - Fullscreen:Width/Height = resolução informada
    - SaveFolder = <Saves persistente>
    """
    try:
        conf = os.path.join(emu_dir, "snes9x.conf")
        if not os.path.exists(conf):
            with open(conf, "w", encoding="utf-8") as f:
                f.write("[Display\\Win]\n")

        try:
            save_folder = _ensure_save_folders(logger)
            save_folder_norm = save_folder.replace("/", "\\")
        except Exception:
            save_folder_norm = save_dir().replace("/", "\\")

        try:
            with open(conf, "r", encoding="utf-8") as f:
                orig = f.read()
        except Exception:
            orig = "[Display\\Win]\n"

        new = orig
        new, _ = re.subn(r"(^\s*Stretch:MaintainAspectRatio\s*=\s*)(TRUE|FALSE)",
                         r"\1FALSE", new, flags=re.M | re.I)
        new, _ = re.subn(r"(^\s*Stretch:Enabled\s*=\s*)(TRUE|FALSE)",
                         r"\1TRUE", new, flags=re.M | re.I)
        new, _ = re.subn(r"(^\s*Fullscreen:Width\s*=\s*)(\d+)",
                         r"\1" + str(width), new, flags=re.M)
        new, _ = re.subn(r"(^\s*Fullscreen:Height\s*=\s*)(\d+)",
                         r"\1" + str(height), new, flags=re.M)

        # Pasta de saves persistente
        if "SaveFolder" in new:
            new, _ = re.subn(r"(^\s*SaveFolder\s*=\s*).*$",
                             r"\1" + save_folder_norm, new, flags=re.M)
        else:
            if not new.endswith("\n"):
                new += "\n"
            new += f"# Persistente\nSaveFolder = {save_folder_norm}\n"

        if new != orig:
            with open(conf, "w", encoding="utf-8") as f:
                f.write(new)
            logger.info("snes9x.conf atualizado para %sx%s (%s)", width, height, conf)
            logger.info("SaveFolder -> %s", save_folder_norm)
    except Exception:
        logger.exception("Falha ao ajustar snes9x.conf")

class Runner(QObject):
    started = Signal()
    finished = Signal()

    def __init__(self, logger):
        super().__init__()
        self.process = None
        self.tmpdir = None
        self.logger = logger

    def _enum_hwnds_for_pid(self, pid: int):
        try:
            import sys
            if not sys.platform.startswith("win"):
                return []
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            EnumWindows = user32.EnumWindows
            EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            GetWindowThreadProcessId = user32.GetWindowThreadProcessId
            matches = []
            def _enum(hwnd, lParam):
                pid_ret = wintypes.DWORD()
                GetWindowThreadProcessId(hwnd, ctypes.byref(pid_ret))
                if pid_ret.value == pid:
                    matches.append(hwnd)
                return True
            EnumWindows(EnumWindowsProc(_enum), 0)
            return matches
        except Exception:
            return []

    def _try_fullscreen_window(self, pid: int, aggressive: bool = True) -> bool:
        try:
            import sys
            if not sys.platform.startswith("win"):
                return False
            import ctypes
            from ctypes import wintypes
            import time as _t
            user32 = ctypes.windll.user32
            SetForegroundWindow = user32.SetForegroundWindow
            ShowWindow = user32.ShowWindow
            GetWindowRect = user32.GetWindowRect
            SetWindowPos = user32.SetWindowPos
            GetSystemMetrics = user32.GetSystemMetrics
            SW_MAXIMIZE = 3
            HWND_TOP = 0
            HWND_TOPMOST = -1
            SWP_NOOWNERZORDER = 0x0200
            SWP_FRAMECHANGED = 0x0020
            SWP_SHOWWINDOW = 0x0040
            TOPMOST_FLAGS = SWP_NOOWNERZORDER | SWP_FRAMECHANGED | SWP_SHOWWINDOW
            VK_MENU = 0x12
            VK_RETURN = 0x0D
            KEYEVENTF_KEYUP = 0x0002

            matches = self._enum_hwnds_for_pid(pid)
            if not matches:
                return False

            sw = GetSystemMetrics(0)
            sh = GetSystemMetrics(1)

            for hwnd in matches:
                try:
                    SetForegroundWindow(hwnd)
                except Exception:
                    pass
                try:
                    keybd_event = user32.keybd_event
                    keybd_event(VK_MENU, 0, 0, 0)
                    keybd_event(VK_RETURN, 0, 0, 0)
                    keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)
                    keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
                except Exception:
                    pass
                _t.sleep(0.25)
                try:
                    rect = wintypes.RECT()
                    if GetWindowRect(hwnd, ctypes.byref(rect)):
                        w = rect.right - rect.left
                        h = rect.bottom - rect.top
                        if w >= sw - 2 and h >= sh - 2:
                            return True
                except Exception:
                    pass
                try:
                    ShowWindow(hwnd, SW_MAXIMIZE)
                    _t.sleep(0.15)
                    rect = wintypes.RECT()
                    if GetWindowRect(hwnd, ctypes.byref(rect)):
                        w = rect.right - rect.left
                        h = rect.bottom - rect.top
                        if w >= sw - 2 and h >= sh - 2:
                            return True
                except Exception:
                    pass
                if aggressive:
                    try:
                        SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, sw, sh, TOPMOST_FLAGS)
                        _t.sleep(0.12)
                        rect2 = wintypes.RECT()
                        if GetWindowRect(hwnd, ctypes.byref(rect2)):
                            w2 = rect2.right - rect2.left
                            h2 = rect2.bottom - rect2.top
                            if w2 >= sw - 2 and h2 >= sh - 2:
                                SetWindowPos(hwnd, HWND_TOP, 0, 0, sw, sh, TOPMOST_FLAGS)
                                return True
                    except Exception:
                        pass
            return False
        except Exception:
            return False

    def _fit_to_monitor(self, pid: int, logger) -> bool:
        try:
            import sys
            if not sys.platform.startswith("win"):
                return False
            import ctypes
            from ctypes import wintypes
            import time as _t
            user32 = ctypes.windll.user32
            matches = self._enum_hwnds_for_pid(pid)
            if not matches:
                return False
            MonitorFromWindow = user32.MonitorFromWindow
            GetMonitorInfoW = user32.GetMonitorInfoW
            class RECT(ctypes.Structure):
                _fields_ = [('left', wintypes.LONG), ('top', wintypes.LONG),
                            ('right', wintypes.LONG), ('bottom', wintypes.LONG)]
            class MONITORINFO(ctypes.Structure):
                _fields_ = [('cbSize', wintypes.DWORD), ('rcMonitor', RECT),
                            ('rcWork', RECT), ('dwFlags', wintypes.DWORD)]
            MONITOR_DEFAULTTONEAREST = 2
            SetWindowPos = user32.SetWindowPos
            HWND_TOP = 0
            HWND_TOPMOST = -1
            SWP_NOOWNERZORDER = 0x0200
            SWP_FRAMECHANGED = 0x0020
            SWP_SHOWWINDOW = 0x0040
            FLAGS = SWP_NOOWNERZORDER | SWP_FRAMECHANGED | SWP_SHOWWINDOW
            for hwnd in matches:
                hmon = MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
                mi = MONITORINFO()
                mi.cbSize = ctypes.sizeof(mi)
                if not GetMonitorInfoW(hmon, ctypes.byref(mi)):
                    continue
                l = mi.rcMonitor.left
                t = mi.rcMonitor.top
                r = mi.rcMonitor.right
                b = mi.rcMonitor.bottom
                w = r - l
                h = b - t
                SetWindowPos(hwnd, HWND_TOPMOST, l, t, w, h, FLAGS)
                _t.sleep(0.10)
                SetWindowPos(hwnd, HWND_TOP, l, t, w, h, FLAGS)
                try:
                    exe, emu_dir = resolve_emulator_exe()
                    _patch_fullscreen_conf(emu_dir, w, h, logger)
                except Exception:
                    pass
                return True
            return False
        except Exception:
            return False

    def _send_alt_enter_after(self, delay_sec: float = 2.5) -> None:
        """
        Aguarda 'delay_sec' e envia ALT+ENTER uma ÚNICA vez.
        Útil quando o emulador entra em fullscreen e logo "cai" para maximizado.
        """
        try:
            import threading, time as _t, sys
            if not sys.platform.startswith("win"):
                return

            def _worker():
                _t.sleep(delay_sec)
                try:
                    import ctypes
                    user32 = ctypes.windll.user32
                    VK_MENU = 0x12
                    VK_RETURN = 0x0D
                    KEYEVENTF_KEYUP = 0x0002
                    user32.keybd_event(VK_MENU, 0, 0, 0)
                    user32.keybd_event(VK_RETURN, 0, 0, 0)
                    user32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)
                    user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
                    try:
                        self.logger.info("ALT+ENTER enviado (gambiarra pós-abertura).")
                    except Exception:
                        pass
                except Exception:
                    pass

            threading.Thread(target=_worker, daemon=True).start()
        except Exception:
            pass

    def run(self, rom_zip_path: str, rom_inside_zip: Optional[str], fullscreen: bool):
        """
        Extrai a ROM selecionada para tmp, lança o emulador e força fullscreen/auto-fit.
        Também garante SaveFolder persistente fora do runtime.
        """
        def _target():
            try:
                self.logger.info("TEMP dir: %s", tempfile.gettempdir())
                try:
                    self.logger.info("ZIP size: %s bytes", os.path.getsize(rom_zip_path))
                except Exception:
                    pass

                rom_zip_path_open = _win_long(rom_zip_path)
                with zipfile.ZipFile(rom_zip_path_open, "r") as zf:
                    bad = zf.testzip()
                    if bad:
                        raise zipfile.BadZipFile(f"Entrada corrompida no ZIP: {bad}")
                    roms = [f for f in zf.namelist() if f.lower().endswith((".sfc", ".smc"))]
                    if not roms:
                        raise RuntimeError("ZIP válido, mas sem ROM .sfc/.smc")
                    chosen = rom_inside_zip or roms[0]
                    self.tmpdir = tempfile.mkdtemp()
                    dest_path = os.path.join(self.tmpdir, os.path.basename(chosen))
                    dest_path_write = _win_long(dest_path)
                    with zipfile.ZipFile(rom_zip_path_open, "r") as zf2:
                        with zf2.open(chosen) as src, open(dest_path_write, "wb") as dst:
                            shutil.copyfileobj(src, dst)

                exe, emu_dir = resolve_emulator_exe()
                _ensure_save_folders(self.logger)
                if fullscreen:
                    try:
                        import ctypes
                        w = ctypes.windll.user32.GetSystemMetrics(0)
                        h = ctypes.windll.user32.GetSystemMetrics(1)
                        _patch_fullscreen_conf(emu_dir, w, h, self.logger)
                    except Exception:
                        self.logger.exception("Não foi possível obter resolução primária")

                cmd = [exe]
                if fullscreen:
                    cmd.append("--fullscreen")
                cmd.append(dest_path)

                self.logger.info("Iniciando emulador: %s", cmd)
                exe_long = _win_long(exe) if os.name == "nt" else exe
                self.process = subprocess.Popen([exe_long] + cmd[1:])
                self.started.emit()

                try:
                    import threading
                    import time as _t
                    import sys as _sys
                    if _sys.platform.startswith("win"):
                        def _enforce():
                            for _ in range(8):  # ~4s
                                proc = self.process
                                if not proc or proc.poll() is not None:
                                    return
                                pid = proc.pid
                                ok1 = self._try_fullscreen_window(pid, aggressive=True)
                                ok2 = self._fit_to_monitor(pid, self.logger)
                                self.logger.info("Fullscreen enforce -> %s | fit -> %s", ok1, ok2)
                                if ok1 or ok2:
                                    return
                                _t.sleep(0.5)
                        threading.Thread(target=_enforce, daemon=True).start()

                        def _f12_toggle_loop():
                            import ctypes
                            user32 = ctypes.windll.user32
                            VK_F12 = 0x7B
                            VK_MENU = 0x12
                            VK_RETURN = 0x0D
                            KEYEVENTF_KEYUP = 0x0002
                            held_since = None
                            cooldown_until = 0.0
                            while True:
                                proc = self.process
                                if not proc or proc.poll() is not None:
                                    return
                                pressed = (user32.GetAsyncKeyState(VK_F12) & 0x8000) != 0
                                now = _t.time()
                                if pressed and now >= cooldown_until:
                                    held_since = held_since or now
                                    if (now - held_since) >= 0.6:
                                        try:
                                            user32.keybd_event(VK_MENU, 0, 0, 0)
                                            user32.keybd_event(VK_RETURN, 0, 0, 0)
                                            user32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)
                                            user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
                                        except Exception:
                                            pass
                                        cooldown_until = now + 0.5
                                        held_since = None
                                else:
                                    held_since = None
                                _t.sleep(0.05)
                        threading.Thread(target=_f12_toggle_loop, daemon=True).start()
                except Exception:
                    pass

                self._send_alt_enter_after(2.5)

                self.process.wait()
            except zipfile.BadZipFile as e:
                self.logger.exception("ZIP inválido/corrompido: %s", e)
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(None, "Erro", f"Arquivo ZIP inválido ou corrompido:\n{rom_zip_path}")
                self.finished.emit(); return
            except (NotImplementedError, ModuleNotFoundError) as e:
                self.logger.exception("Método de compressão do ZIP não suportado: %s", e)
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(None, "Erro",
                    "Método de compressão do ZIP não suportado no executável.\n"
                    "Recompacte o arquivo em 'Deflate' ou atualize o build com bz2/lzma.")
                self.finished.emit(); return
            except PermissionError as e:
                self.logger.exception("Permissão negada: %s", e)
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(None, "Erro", "Sem permissão para ler o ZIP ou escrever no TEMP.")
                self.finished.emit(); return
            except OSError as e:
                from PySide6.QtWidgets import QMessageBox
                if getattr(e, "errno", None) == errno.ENOSPC:
                    msg = "Sem espaço em disco para extrair a ROM (TEMP/drive)."
                else:
                    msg = f"Falha de E/S ao extrair: {e.strerror or e}"
                self.logger.exception(msg)
                QMessageBox.critical(None, "Erro", msg)
                self.finished.emit(); return
            except Exception as e:
                self.logger.exception("Erro ao executar ROM: %s", e)
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(None, "Erro", f"Erro ao executar ROM:\n{e}")
                self.finished.emit(); return
            finally:
                try:
                    if self.tmpdir and os.path.isdir(self.tmpdir):
                        shutil.rmtree(self.tmpdir)
                except Exception:
                    self.logger.exception("Erro ao limpar tmp")
                self.process = None
                self.tmpdir = None
                self.finished.emit()

        import threading
        threading.Thread(target=_target, daemon=True).start()

    def run_with_type(self, tipo: str, path: str, rom_inside_zip: Optional[str], fullscreen: bool):
        """
        tipo = "zip" ou "rom"
        - zip: usa fluxo de extração (run)
        - rom: executa o arquivo diretamente (.sfc/.smc)
        """
        if tipo == "zip":
            return self.run(path, rom_inside_zip, fullscreen)

        def _target():
            try:
                exe, emu_dir = resolve_emulator_exe()
                _ensure_save_folders(self.logger)
                if fullscreen:
                    try:
                        import ctypes
                        w = ctypes.windll.user32.GetSystemMetrics(0)
                        h = ctypes.windll.user32.GetSystemMetrics(1)
                        _patch_fullscreen_conf(emu_dir, w, h, self.logger)
                    except Exception:
                        self.logger.exception("Não foi possível obter resolução primária")

                cmd = [exe]
                if fullscreen:
                    cmd.append("--fullscreen")
                cmd.append(path)

                self.logger.info("Iniciando emulador (ROM direta): %s", cmd)
                exe_long = _win_long(exe) if os.name == "nt" else exe
                self.process = subprocess.Popen([exe_long] + cmd[1:])
                self.started.emit()

                try:
                    import threading, time as _t, sys as _sys
                    if _sys.platform.startswith("win"):
                        def _enforce():
                            for _ in range(8):
                                proc = self.process
                                if not proc or proc.poll() is not None:
                                    return
                                pid = proc.pid
                                ok1 = self._try_fullscreen_window(pid, aggressive=True)
                                ok2 = self._fit_to_monitor(pid, self.logger)
                                self.logger.info("Fullscreen enforce -> %s | fit -> %s", ok1, ok2)
                                if ok1 or ok2:
                                    return
                                _t.sleep(0.5)
                        threading.Thread(target=_enforce, daemon=True).start()

                        def _f12_toggle_loop():
                            import ctypes
                            user32 = ctypes.windll.user32
                            VK_F12 = 0x7B
                            VK_MENU = 0x12
                            VK_RETURN = 0x0D
                            KEYEVENTF_KEYUP = 0x0002
                            held_since = None
                            cooldown_until = 0.0
                            while True:
                                proc = self.process
                                if not proc or proc.poll() is not None:
                                    return
                                pressed = (user32.GetAsyncKeyState(VK_F12) & 0x8000) != 0
                                now = _t.time()
                                if pressed and now >= cooldown_until:
                                    held_since = held_since or now
                                    if (now - held_since) >= 0.6:
                                        try:
                                            user32.keybd_event(VK_MENU, 0, 0, 0)
                                            user32.keybd_event(VK_RETURN, 0, 0, 0)
                                            user32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)
                                            user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
                                        except Exception:
                                            pass
                                        cooldown_until = now + 0.5
                                        held_since = None
                                else:
                                    held_since = None
                                _t.sleep(0.05)
                        threading.Thread(target=_f12_toggle_loop, daemon=True).start()
                except Exception:
                    pass

                self._send_alt_enter_after(2.5)

                self.process.wait()
            except Exception as e:
                self.logger.exception("Erro ao executar ROM direta: %s", e)
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(None, "Erro", f"Erro ao executar ROM:\n{e}")
                self.finished.emit(); return
            finally:
                self.process = None
                self.tmpdir = None
                self.finished.emit()

        import threading
        threading.Thread(target=_target, daemon=True).start()

    def stop(self):
        """
        Fecha o emulador de forma amigável e, se necessário, força encerramento.
        Tolerante a condição de corrida (self.process pode virar None enquanto executa).
        """
        try:
            proc = getattr(self, "process", None)
            if not proc:
                return
            try:
                if proc.poll() is not None:
                    return
            except Exception:
                return

            import sys
            if sys.platform.startswith("win"):
                import ctypes
                from ctypes import wintypes
                import time as _t
                user32 = ctypes.windll.user32
                PostMessageW = user32.PostMessageW
                WM_CLOSE = 0x0010

                try:
                    pid = getattr(proc, "pid", None)
                    if pid is not None:
                        matches = self._enum_hwnds_for_pid(pid)
                        for hwnd in matches:
                            try:
                                PostMessageW(hwnd, WM_CLOSE, 0, 0)
                            except Exception:
                                pass
                except Exception:
                    pass

                for _ in range(10):
                    proc_now = getattr(self, "process", None) or proc
                    try:
                        if not proc_now or proc_now.poll() is not None:
                            break
                    except Exception:
                        break
                    _t.sleep(0.1)

                proc_now = getattr(self, "process", None) or proc
                try:
                    if proc_now and proc_now.poll() is None:
                        proc_now.terminate()
                except Exception:
                    pass

                for _ in range(10):
                    proc_now = getattr(self, "process", None) or proc
                    try:
                        if not proc_now or proc_now.poll() is not None:
                            break
                    except Exception:
                        break
                    _t.sleep(0.1)

                proc_now = getattr(self, "process", None) or proc
                try:
                    if proc_now and proc_now.poll() is None:
                        proc_now.kill()
                except Exception:
                    pass
        except Exception:
            self.logger.exception("Erro ao terminar emulador")
