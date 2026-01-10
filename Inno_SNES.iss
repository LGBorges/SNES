
; Instala TUDO em {userdocs}\Saved Games\SNES\Saves (sem precisar de admin)

#define MyAppName "SNES"
#define MyAppVersion "1.0"
#define MyAppPublisher "Leônidas"
#define MyAppURL "https://github.com/LGBorges/SNES"
#define MyAppExeName "SNESLauncher.exe"
#define MyAppAssocName MyAppName + " File"
#define MyAppAssocExt ".myp"
#define MyAppAssocKey StringChange(MyAppAssocName, " ", "") + MyAppAssocExt

[Setup]
AppId={{FC79BA55-1E96-4316-B79D-E8F837A4E16A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; >>> Instalação diretamente em Saved Games do usuário
DefaultDirName={userdocs}\Saved Games\SNES

UninstallDisplayIcon={app}\{#MyAppExeName}

; Compatível com x64, mas não instalaremos em "64‑bit mode"
ArchitecturesAllowed=x64compatible
; ArchitecturesInstallIn64BitMode=   ; (intencionalmente omitido)

ChangesAssociations=yes

; Não mostra página de grupo do Menu Iniciar (criamos atalhos automaticamente)
DisableProgramGroupPage=yes

; >>> Sem admin/UAC; instalação por usuário
PrivilegesRequired=lowest

; (Opcional) não mostrar a página para escolher a pasta
DisableDirPage=no

; Saída do compilador (onde o instalador .exe será gerado)
OutputDir=D:\SNES_EXE\release
OutputBaseFilename=Instalador_SNES
SetupIconFile=D:\SNES_EXE\snes_launcher.ico
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english";    MessagesFile: "compiler:Default.isl"
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Seu executável será instalado na pasta de Saves (DefaultDirName)
Source: "D:\SNES_EXE\dist\SNESLauncher.exe"; DestDir: "{app}"; Flags: ignoreversion

[Registry]
; Associações (se realmente usar a extensão .myp). Mantidas como você tinha.
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocExt}\OpenWithProgids"; ValueType: string; ValueName: "{#MyAppAssocKey}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}"; ValueType: string; ValueName: ""; ValueData: "{#MyAppAssocName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

[Icons]
; Atalhos apontando para o EXE dentro de {app} (Saved Games)
Name: "{autoprograms}\SNESLauncher"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\SNESLauncher"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
; Executar ao final da instalação
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,SNES}"; Flags: nowait postinstall skipifsilent
