[Setup]
AppId=TeamsAI.Local.Windows
AppName=TeamsAI
AppVersion=1.0.0
DefaultDirName={localappdata}\Programs\TeamsAI
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\output
OutputBaseFilename=TeamsAI-Setup
Compression=none
DiskSpanning=yes
DiskSliceSize=1500000000
SlicesPerDisk=1
WizardStyle=modern
UninstallDisplayIcon={app}\TeamsAI.exe
CloseApplications=yes
SetupLogging=yes
[Languages]
Name: "mn"; MessagesFile: "Mongolian.isl"
[Files]
Source: "..\dist\TeamsAI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{autoprograms}\TeamsAI"; Filename: "{app}\TeamsAI.exe"
Name: "{autodesktop}\TeamsAI"; Filename: "{app}\TeamsAI.exe"
[Run]
Filename: "{app}\TeamsAI.exe"; Description: "TeamsAI эхлүүлэх"; Flags: nowait postinstall skipifsilent
[Messages]
mn.WelcomeLabel1=TeamsAI суулгах
mn.WelcomeLabel2=Монгол OCR, локал AI хөдөлгүүр болон модель хамт сууна.%n%nНэмэлт Python, Ollama, API түлхүүр шаардлагагүй.
