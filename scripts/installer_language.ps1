$ErrorActionPreference='Stop'
$base="${env:ProgramFiles(x86)}\Inno Setup 6\Default.isl"
$text=Get-Content $base -Raw
$translations=@{
LanguageName='Монгол'; LanguageID='$0450'; LanguageCodePage='0';
ButtonNext='Дараах >'; ButtonBack='< Буцах'; ButtonCancel='Болих'; ButtonInstall='Суулгах'; ButtonFinish='Дуусгах';
SetupWindowTitle='%1 суулгах'; SelectDirLabel3='Программыг дараах хавтаст суулгана.';
WizardInstalling='Суулгаж байна'; InstallingLabel='Түр хүлээнэ үү. Программыг суулгаж байна.';
FinishedHeadingLabel='Суулгаж дууслаа'; FinishedLabelNoIcons='[name] таны компьютерт суулаа.';
WizardSelectDir='Суулгах хавтас'; WizardReady='Суулгахад бэлэн'; ReadyLabel1='Суулгах товчийг дарж үргэлжлүүлнэ үү.';
ConfirmTitle='Баталгаажуулах'; ExitSetupTitle='Суулгалтыг зогсоох'; Yes='Тийм'; No='Үгүй'; OK='За'
}
foreach($key in $translations.Keys) { $text=[regex]::Replace($text,"(?m)^$key=.*$",($key+'='+$translations[$key])) }
[IO.File]::WriteAllText((Join-Path $PSScriptRoot '../installer/Mongolian.isl'),$text,[Text.UTF8Encoding]::new($true))
