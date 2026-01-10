# PARA CRIAR O EXECUTAVEL NO WINDOWS - Executar no PowerShell
 1 - cd /PATH/TO/SNES_FILES -> cd D:\SNES_EXE\ <br>
 2 - Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser<br>
 3 - Executar o comando: .\.venv\Scripts\python -m PyInstaller --onefile --noconsole --disable-windowed-traceback --name SNESLauncher --icon snes_launcher.ico --collect-all PySide6 --collect-submodules PySide6 --collect-data PySide6 --add-data "Roms;Roms" --add-data "snes_bg.png;." --add-data "snes9x-x64.exe;." --add-data "snes_launcher.ico;." src\main.py

Como subir as ROMs para o git,:

- Mover os arquivos internos para a pasta Roms/ \
  cd /PATH/TO/SNES_FILES \
  dest="/PATH/TO/SNES_FILES/Roms" \
  find "Roms/jogos" -type f -print0 | xargs -0 -I{} sh -c 'echo "MOVENDO: {} -> '"$dest"'" && mv -v -- "{}" "'"$dest"'"'

- Usar o git lfs para subir arquivos maiores que 100Mb, dentro do /PATH/TO/SNES_FILES \
  git lfs track "*.smc" \
  git lfs track "*.sfc" \
  git lfs track "*.zip" \
  git lfs track "*.bin" \
  git lfs track "*.nes" \
  git add .gitattributes

- Git add, Git commit e Git push \
  git add . \
  git commit -m "Adicionando ROMs no diretório Roms/" \
  git push -u origin main \
  User: user_git \
  Pass: gerar token -> https://github.com/settings/tokens

  


 
 ----------------------------------------------------------------
 ----------------------------------------------------------------
 ----------------------------------------------------------------
 ----------------------------------------------------------------
 ----------------------------------------------------------------
 ----------------------------------------------------------------
 <h3>NÃO USAR, a não ser que saiba o que está fazendo:</h3><br>
      python3 -m venv .venv<br>
      .venv\Scripts\python -m pip install -r requirements.txt<br>
