# PARA CRIAR O EXECUTAVEL NO WINDOWS - Executar no PowerShell
 1 - cd PATH/TO/SNES_FILES -> cd D:\SNES_EXE\ <br>
 2 - Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser<br>
 3 - Executar o comando: .\.venv\Scripts\python -m PyInstaller --onefile --noconsole --disable-windowed-traceback --name SNESLauncher --icon snes_launcher.ico --collect-all PySide6 --collect-submodules PySide6 --collect-data PySide6 --add-data "Roms;Roms" --add-data "snes_bg.png;." --add-data "snes9x-x64.exe;." --add-data "snes_launcher.ico;." src\main.py
 ----------------------------------------------------------------
 ----------------------------------------------------------------
 ----------------------------------------------------------------
 ----------------------------------------------------------------
 ----------------------------------------------------------------
 ----------------------------------------------------------------
 <h3>NÃO USAR, a não ser que saiba o que está fazendo:</h3><br>
      python3 -m venv .venv<br>
      .venv\Scripts\python -m pip install -r requirements.txt<br>
