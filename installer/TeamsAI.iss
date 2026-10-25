[Setup]
AppId=TeamsAI.Local.Windows
AppName=BORO
AppVersion=1.3.0
DefaultDirName={localappdata}\Programs\TeamsAI
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\output
OutputBaseFilename=BORO-Setup
Compression=none
DiskSpanning=yes
DiskSliceSize=1500000000
SlicesPerDisk=1
WizardStyle=modern
UninstallDisplayIcon={app}\BORO.exe
CloseApplications=yes
SetupLogging=yes
[Languages]
Name: "mn"; MessagesFile: "Mongolian.isl"
[Files]
Source: "..\dist\BORO\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{autoprograms}\BORO"; Filename: "{app}\BORO.exe"
Name: "{autodesktop}\BORO"; Filename: "{app}\BORO.exe"
[Run]
Filename: "{app}\BORO.exe"; Description: "BORO эхлүүлэх"; Flags: nowait postinstall skipifsilent
[Messages]
mn.WelcomeLabel1=BORO суулгах
mn.WelcomeLabel2=Монгол OCR, локал AI хөдөлгүүр болон модель хамт сууна.%n%nНэмэлт Python, Ollama, API түлхүүр шаардлагагүй.
