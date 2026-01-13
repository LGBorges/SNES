# PARA CRIAR O EXECUTAVEL NO WINDOWS - Executar pelo PowerShell - Em Desenvolvimento...

 1. Depois de clonar o projeto \
cd /PATH/TO/SNES_FILES 
 2. Executar o comando no PowerShell se tiver no path /mnt/{c | d}/SNES \
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser 
 3. Ativar o venv(se não tiver o python instalado, INSTALE, junto com o venv e o pip): \
python3 -m venv .venv \
.venv\Scripts\python.exe -m pip install --upgrade pip
 4. Instalar com pip os requirements \
.venv\Scripts\python.exe -m pip install -r requirements.txt
 5. Executar o comando: \
.venv\Scripts\python.exe -m PyInstaller --onefile --noconsole --disable-windowed-traceback --name SNESLauncher --icon snes_launcher.ico --collect-all PySide6 --collect-submodules PySide6 --collect-data PySide6 --add-data "Roms;Roms" --add-data "snes_bg.png;." --add-data "snes9x-x64.exe;." --add-data "snes_launcher.ico;." src\main.py

Talvez seja necessário esses comado do git lfs: 

git lfs install \
git lfs fetch --all \
git lfs pull \
git lfs checkout

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



