import os, zipfile, json
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QListWidget,
    QListWidgetItem, QPushButton, QLabel, QLineEdit, QMessageBox, QCheckBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFontMetrics

from app.roms import carregar_jogos
from app.paths import rom_root, save_dir
from app.config import load_gui_settings, save_gui_settings
from app.runner import Runner
from app.resources import load_background


class MainWindow(QMainWindow):
    def __init__(self, logger):
        super().__init__()
        self.logger = logger
        self.setWindowTitle("SNES Launcher")
        self.resize(1000, 700)

        self._busy_launch = False
        self._translucent_enabled = True
        self._opacity_value = 90

        self.runner = Runner(logger)
        self.runner.started.connect(self.on_started)
        self.runner.finished.connect(self.on_finished)

        self._build_ui()
        self._load_games()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        self.bg_pixmap = load_background()
        if self.bg_pixmap:
            self.bg_label = QLabel(central)
            self.bg_label.setScaledContents(True)
            self.bg_label.setPixmap(self.bg_pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
            self.bg_label.setGeometry(self.rect())
            self.bg_label.lower()
        else:
            central.setStyleSheet('background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1b1b1b, stop:1 #0f0f0f);')

        left = QVBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Pesquisar por nome do jogo...")
        self.search.textChanged.connect(self.filter_games)
        left.addWidget(self.search)

        self.list_games = QListWidget()
        self.list_games.itemSelectionChanged.connect(self.on_game_selected)
        self.list_games.itemDoubleClicked.connect(self.on_double_click)
        left.addWidget(self.list_games)

        btns_left = QHBoxLayout()
        self.btn_refresh = QPushButton("Recarregar")
        self.btn_refresh.clicked.connect(self._load_games)
        self.btn_open = QPushButton("Abrir pasta Roms")
        self.btn_open.clicked.connect(self.open_roms_folder)
        btns_left.addWidget(self.btn_refresh)
        btns_left.addWidget(self.btn_open)
        left.addLayout(btns_left)

        right = QVBoxLayout()
        self.lbl_selected = QLabel("Selecione um jogo para ver detalhes")
        self.lbl_selected.setWordWrap(True)
        right.addWidget(self.lbl_selected)

        self.list_internal = QListWidget()
        right.addWidget(self.list_internal)

        btns = QHBoxLayout()
        self.btn_continue = QPushButton("Continuar")
        self.btn_continue.clicked.connect(self.continuar_ultimo)
        self.btn_run = QPushButton("Executar")
        self.btn_run.clicked.connect(self.run_selected)
        self.btn_stop = QPushButton("Parar")
        self.btn_stop.clicked.connect(self.stop_running)
        self.btn_stop.setEnabled(False)
        btns.addWidget(self.btn_continue)
        btns.addWidget(self.btn_run)
        btns.addWidget(self.btn_stop)
        right.addLayout(btns)

        splitter = QSplitter()
        lw, rw = QWidget(), QWidget()
        lw.setLayout(left); rw.setLayout(right)
        splitter.addWidget(lw); splitter.addWidget(rw)
        root.addWidget(splitter)

        controls_appear = QHBoxLayout()
        self.chk_translucent = QCheckBox("Painéis translúcidos")
        self.chk_translucent.toggled.connect(self.on_translucent_toggled)
        controls_appear.addWidget(self.chk_translucent)

        self.btn_exit = QPushButton("Sair")
        self.btn_exit.clicked.connect(self.on_exit_clicked)
        controls_appear.addWidget(self.btn_exit)

        s = load_gui_settings(save_path=self._save_path())
        self._hint_text = s.get('hint_text', 'Tela cheia: ALT+ENTER (alternar) • ou segure F12 por 0,6s')
        self.hint_fullscreen = QLabel(self._hint_text)

        self._translucent_enabled = bool(s.get("translucent", True))
        self._opacity_value = int(s.get("opacity", 90))
        self.chk_translucent.setChecked(self._translucent_enabled)
        self._apply_hint_style(self._translucent_enabled)
        self.hint_fullscreen.setWordWrap(True)
        controls_appear.addWidget(self.hint_fullscreen)
        right.addLayout(controls_appear)

        self.apply_transparency(self._translucent_enabled)
        self.apply_controls_style()

        self.status = self.statusBar()
        self.status.showMessage("Pronto")

        self._refresh_continue_button()

    def _save_path(self) -> str:
        path = save_dir()
        os.makedirs(path, exist_ok=True)
        return path

    def _apply_hint_style(self, enabled: bool):
        alpha = 0.55 if enabled else 0.40
        self.hint_fullscreen.setStyleSheet(
            f'background-color: rgba(0,0,0,{alpha});'
            'color: #ffffff; padding:6px 10px; border-radius:6px;'
            'border: 1px solid rgba(255,255,255,0.08);'
        )

    def apply_transparency(self, enabled: bool):
        self._translucent_enabled = bool(enabled)
        self._opacity_value = 90 if enabled else 10
        alpha = self._opacity_value / 100.0
        panel_style = (
            f"background-color: rgba(0,0,0,{alpha});"
            "border: 1px solid rgba(255,255,255,0.06);"
            "border-radius:6px;"
            "color: #ffffff;"
        )
        self.list_games.setStyleSheet(panel_style)
        self.list_internal.setStyleSheet(panel_style)
        search_bg = f"rgba(255,255,255,{0.85 if enabled else 0.35})"
        search_bg_focus = f"rgba(255,255,255,{0.95 if enabled else 0.45})"
        self.search.setStyleSheet(
            f"QLineEdit {{ background-color: {search_bg}; color: black; "
            f"border: 1px solid rgba(0,0,0,0.14); padding:8px 10px; border-radius:6px; }}"
            f"QLineEdit:focus {{ background-color: {search_bg_focus}; }}"
        )
        s = load_gui_settings(save_path=self._save_path())
        s.update({"translucent": self._translucent_enabled, "opacity": self._opacity_value})
        save_gui_settings(save_path=self._save_path(), settings=s)
        self._apply_hint_style(self._translucent_enabled)

    def on_translucent_toggled(self, checked: bool):
        self.apply_transparency(bool(checked))
        self._refresh_continue_button()

    def apply_controls_style(self):
        styles = {
            "continue": "background-color: rgb(33,150,243); color: white; font-weight:600;",
            "run": "background-color: rgb(76,175,80); color: white; font-weight:600;",
            "stop": "background-color: rgb(255,235,59); color: black; font-weight:600;",
            "exit": "background-color: rgb(244,67,54); color: white; font-weight:600;",
        }
        self.btn_continue.setStyleSheet(styles["continue"])
        self.btn_run.setStyleSheet(styles["run"])
        self.btn_stop.setStyleSheet(styles["stop"])
        self.btn_exit.setStyleSheet(styles["exit"])

    def _refresh_continue_button(self):
        tipo, rel_path, _ = self._load_last_played()
        if not rel_path:
            self.btn_continue.setText("Continuar")
            return
        nome = os.path.splitext(os.path.basename(rel_path))[0]
        rotulo = f"Continuar ({nome})"
        fm = QFontMetrics(self.btn_continue.font())
        maxw = max(120, self.btn_continue.width() - 12)
        elided = fm.elidedText(rotulo, Qt.ElideRight, maxw)
        self.btn_continue.setText(elided)

    def _save_last_played(self, tipo: str, rel_path: str, rom_interna):
        s = load_gui_settings(save_path=self._save_path())
        s["last_played"] = {"tipo": tipo, "rel_path": rel_path, "rom_interna": rom_interna}
        save_gui_settings(save_path=self._save_path(), settings=s)
        txt = os.path.join(self._save_path(), "ultimo_jogo.txt")
        with open(txt, "w", encoding="utf-8") as f:
            f.write(f"{tipo}|{rel_path}|{'' if rom_interna is None else rom_interna}")
        self._refresh_continue_button()

    def _load_last_played(self):
        s = load_gui_settings(save_path=self._save_path())
        lp = s.get("last_played") or {}
        tipo = lp.get("tipo")
        rel_path = lp.get("rel_path")
        rom_interna = lp.get("rom_interna")
        if tipo in ("zip", "rom") and rel_path:
            return tipo, rel_path, rom_interna
        txt = os.path.join(self._save_path(), "ultimo_jogo.txt")
        if os.path.exists(txt):
            line = open(txt, "r", encoding="utf-8").read().strip()
            parts = line.split("|")
            if len(parts) >= 2:
                tipo = parts[0].strip()
                rel_path = parts[1].strip()
                rom_interna = parts[2].strip() if len(parts) >= 3 and parts[2].strip() else None
                return tipo, rel_path, rom_interna
        return None, None, None

    def _load_games(self):
        self.all_games = carregar_jogos()
        self.filtered_games = list(self.all_games)
        self._refresh_game_list()

    def _refresh_game_list(self):
        self.list_games.clear()
        for tipo, rel_path in self.filtered_games:
            rotulo = os.path.splitext(os.path.basename(rel_path))[0]
            item = QListWidgetItem(rotulo)
            item.setData(Qt.UserRole, (tipo, rel_path))
            self.list_games.addItem(item)
        self.status.showMessage(f"{len(self.filtered_games)} jogos")

    def filter_games(self, text: str):
        text = text.lower().strip()
        if not text:
            self.filtered_games = list(self.all_games)
        else:
            self.filtered_games = [
                (tipo, rel_path) for (tipo, rel_path) in self.all_games
                if text in os.path.splitext(os.path.basename(rel_path))[0].lower()
            ]
        self._refresh_game_list()

    def on_game_selected(self):
        items = self.list_games.selectedItems()
        if not items:
            self.lbl_selected.setText("Selecione um jogo para ver detalhes")
            self.list_internal.clear()
            return
        tipo, rel_path = items[0].data(Qt.UserRole)
        self.lbl_selected.setText(rel_path)
        self._populate_internal(tipo, rel_path)

    def _populate_internal(self, tipo: str, rel_path: str):
        self.list_internal.clear()
        base_path = rom_root()
        full_path = os.path.join(base_path, rel_path)
        if tipo == "zip":
            try:
                with zipfile.ZipFile(full_path, "r") as zf:
                    roms = [f for f in zf.namelist() if f.lower().endswith((".sfc", ".smc"))]
                    for r in roms:
                        item = QListWidgetItem(os.path.basename(r))
                        item.setData(Qt.UserRole, r)
                        self.list_internal.addItem(item)
            except Exception as e:
                QMessageBox.warning(self, "Erro", f"Não foi possível listar o ZIP:\n{e}")
        else:
            item = QListWidgetItem(os.path.basename(full_path))
            item.setData(Qt.UserRole, None)
            self.list_internal.addItem(item)

    def get_selected_zip_and_rom(self):
        items = self.list_games.selectedItems()
        if not items:
            return None, None, None
        tipo, rel_path = items[0].data(Qt.UserRole)
        rom_item = self.list_internal.selectedItems()
        rom_interna = rom_item[0].data(Qt.UserRole) if rom_item else None
        return tipo, rel_path, rom_interna

    def run_selected(self):
        if self._busy_launch:
            return
        tipo, rel_path, rom_interna = self.get_selected_zip_and_rom()
        if not rel_path:
            QMessageBox.information(self, "Selecione", "Selecione um jogo primeiro.")
            return
        self._save_last_played(tipo, rel_path, rom_interna)
        self._busy_launch = True
        self.status.showMessage(f"Executando {rel_path}...")
        for b in (self.btn_run, self.btn_refresh, self.btn_continue): b.setEnabled(False)
        self.btn_stop.setEnabled(True)
        fullscreen = True
        full_path = os.path.join(rom_root(), rel_path)
        self.runner.run_with_type(tipo, full_path, rom_interna, fullscreen=fullscreen)

    def stop_running(self):
        self.status.showMessage("Parando...")
        self.runner.stop()

    def on_started(self):
        self._busy_launch = False
        self.status.showMessage("Em execução")
        self.btn_exit.setEnabled(False)

    def on_finished(self):
        self.status.showMessage("Parado")
        for b in (self.btn_run, self.btn_refresh, self.btn_continue): b.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._refresh_continue_button()
        QTimer.singleShot(500, lambda: self.btn_exit.setEnabled(True))

    def continuar_ultimo(self):
        tipo, rel_path, rom_interna = self._load_last_played()
        if not rel_path:
            QMessageBox.information(self, "Nenhum", "Ainda não há jogo recente para continuar.")
            return
        self._busy_launch = True
        self.status.showMessage(f"Executando (continuar) {rel_path}...")
        for b in (self.btn_run, self.btn_refresh, self.btn_continue): b.setEnabled(False)
        self.btn_stop.setEnabled(True)
        fullscreen = True
        full_path = os.path.join(rom_root(), rel_path)
        self.runner.run_with_type(tipo, full_path, rom_interna, fullscreen=fullscreen)

    def open_roms_folder(self):
        path = rom_root()
        if os.path.exists(path):
            import subprocess, sys
            try:
                if sys.platform.startswith("win"):
                    os.startfile(path)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", path])
                else:
                    subprocess.Popen(["xdg-open", path])
            except Exception:
                QMessageBox.warning(self, "Erro", "Não foi possível abrir a pasta.")
        else:
            QMessageBox.warning(self, "Erro", "Pasta Roms não encontrada.")

    def on_exit_clicked(self):
        if getattr(self.runner, "process", None):
            self.stop_running()
            QTimer.singleShot(250, self.close_app)
        else:
            self.close_app()

    def close_app(self):
        from PySide6.QtWidgets import QApplication
        QApplication.quit()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        if getattr(self, "bg_pixmap", None):
            self.bg_label.setPixmap(self.bg_pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
            self.bg_label.setGeometry(self.rect()); self.bg_label.lower()
        self._refresh_continue_button()

    def on_double_click(self, item):
        self.run_selected()
