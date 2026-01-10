import os, json

MIN_OPACITY = 25
DEFAULTS = {
    "translucent": True,
    "opacity": MIN_OPACITY,
    "fullscreen": True,
    "longpress_enabled": True,
    "longpress_key": "F12",
    "longpress_threshold": 600,  # ms
    "xinput_enabled": True,
    "xinput_button": "BACK",
    "aggressive_fullscreen": True,
    # Dica padrão (alinhar com a GUI)
    "hint_text": "Tela cheia: ALT+ENTER (alternar) • ou segure F12 por 0,6s",
    # Importante: documenta e permite persistir o último jogado
    "last_played": None,  # dict {"tipo": "zip|rom", "rel_path": "...", "rom_interna": "...|None"} ou None
}

def settings_path(save_path: str) -> str:
    return os.path.join(save_path, "gui_settings.json")

def load_gui_settings(save_path: str) -> dict:
    """
    Carrega JSON e preserva TODAS as chaves presentes no arquivo.
    Defaults completam apenas o que estiver faltando.
    """
    try:
        p = settings_path(save_path)
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            # mantém tudo do arquivo; preenche faltantes com DEFAULTS
            out = dict(DEFAULTS)
            out.update(data)
            return out
    except Exception:
        pass
    # fallback: só defaults
    return dict(DEFAULTS)

def save_gui_settings(save_path: str, settings: dict) -> None:
    """
    Salva o dicionário inteiro, sem filtrar chaves.
    """
    try:
        os.makedirs(save_path, exist_ok=True)
        with open(settings_path(save_path), "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
