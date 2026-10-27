$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
python -m pip install -r requirements.txt
if ($LASTEXITCODE) { throw 'Dependencies failed' }
python scripts/make_branding.py
if ($LASTEXITCODE) { throw 'Branding failed' }
python -m unittest discover -s tests -v
if ($LASTEXITCODE) { throw 'Tests failed' }
python scripts/prepare_assets.py
if ($LASTEXITCODE) { throw 'Assets failed' }
python scripts/verify_ocr_layouts.py
if ($LASTEXITCODE) { throw 'Mongolian OCR layout regression failed' }
python app.py --self-test
if ($LASTEXITCODE) { throw 'Real OCR/AI smoke failed' }
python -m PyInstaller --clean --noconfirm --onedir --windowed --icon branding/boro.ico --name BORO app.py
if ($LASTEXITCODE) { throw 'App build failed' }
Copy-Item assets dist/BORO/assets -Recurse
Copy-Item branding dist/BORO/branding -Recurse
# Self-test of the frozen executable: windowed executable has no console, wait explicitly.
$p=Start-Process dist/BORO/BORO.exe -ArgumentList '--self-test' -PassThru -Wait
if ($p.ExitCode -ne 0) { throw 'Frozen smoke failed' }
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" installer/TeamsAI.iss
if ($LASTEXITCODE) { throw 'Installer failed' }
