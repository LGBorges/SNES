import os
from .paths import rom_root

def carregar_jogos() -> list[tuple[str, str]]:
    """
    Retorna lista de tuplas (tipo, caminho_relativo).
      - tipo = "zip" para arquivos .zip
      - tipo = "rom" para arquivos .sfc/.smc

    Faz busca RECURSIVA em Roms\jogos e retorna caminhos relativos
    ao rom_root(), p.ex.: "ActRaiser (USA)\ActRaiser (USA).sfc"
    """
    root = rom_root()
    entries: list[tuple[str, str]] = []
    try:
        for dirpath, _, filenames in os.walk(root):
            rel_dir = os.path.relpath(dirpath, root)
            rel_dir = "" if rel_dir == "." else rel_dir

            for f in filenames:
                fl = f.lower()
                if fl.endswith(".zip"):
                    rel = f if not rel_dir else os.path.join(rel_dir, f)
                    entries.append(("zip", rel))
                elif fl.endswith(".sfc") or fl.endswith(".smc"):
                    rel = f if not rel_dir else os.path.join(rel_dir, f)
                    entries.append(("rom", rel))

        # Ordena por nome (sem extensão), usando o basename
        entries.sort(key=lambda x: os.path.splitext(os.path.basename(x[1]))[0].lower())
        return entries
    except Exception:
        return []
