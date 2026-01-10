import os, sys, logging

def setup_logger(save_path: str) -> logging.Logger:
    os.makedirs(save_path, exist_ok=True)
    log_file = os.path.join(save_path, "SNES.log")
    logger = logging.getLogger("SNESLauncher")
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt); logger.addHandler(fh)
    try:
        if sys.stderr:
            sh = logging.StreamHandler(); sh.setFormatter(fmt)
            logger.addHandler(sh)
    except Exception:
        pass
    return logger
