import hashlib,json,platform,shutil,subprocess,plistlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];arch='arm64' if platform.machine()=='arm64' else 'x64';out=ROOT/'output';out.mkdir(exist_ok=True)
app=ROOT/'dist/BORO.app';assets=app/'Contents/Resources/assets';shutil.copytree(ROOT/'assets',assets,dirs_exist_ok=True)
shutil.copytree(ROOT/'branding',app/'Contents/Resources/branding',dirs_exist_ok=True)
# Native dylibs are already relocated/signed; sign the full bundle after assets are copied.
subprocess.run(['codesign','--force','--deep','--sign','-',str(app)],check=True)
subprocess.run(['codesign','--verify','--deep','--strict',str(app)],check=True)
subprocess.run([str(app/'Contents/MacOS/BORO'),'--self-test'],check=True,timeout=300)
stage=ROOT/'package-root';stage.mkdir(exist_ok=True);shutil.copytree(app,stage/'BORO.app',dirs_exist_ok=True,symlinks=True)
pkg=out/f'BORO-{arch}.pkg'
component=ROOT/'components.plist'
component.write_bytes(plistlib.dumps([{'RootRelativeBundlePath':'BORO.app','BundleIsRelocatable':False,'BundleIsVersionChecked':False,'BundleHasStrictIdentifier':True,'BundleOverwriteAction':'upgrade'}]))
subprocess.run(['pkgbuild','--root',str(stage),'--component-plist',str(component),'--identifier','studio.rainy.boro','--version','1.3.0','--install-location','/Applications',str(pkg)],check=True)
# GitHub release assets have a per-file size ceiling. Keep every download below 1.5GB.
h=hashlib.sha256();parts=[]
with pkg.open('rb') as src:
    i=1
    while data:=src.read(1_400_000_000):
        path=out/f'BORO-{arch}.pkg.part{i:02}';path.write_bytes(data);h.update(data);parts.append(path.name);i+=1
command=out/f'Install-BORO-{arch}.command'
command.write_text('''#!/bin/sh
set -eu
cd "$(dirname "$0")"
echo 'BORO суулгах багцыг нэгтгэж байна…'
'''+f'cat '+ ' '.join('"'+p+'"' for p in parts)+f' > "BORO-{arch}.pkg"\n'+f'echo "{h.hexdigest()}  BORO-{arch}.pkg" | /usr/bin/shasum -a 256 -c -\n'+f'open "BORO-{arch}.pkg"\n')
command.chmod(0o755)
(out/f'BORO-{arch}-SHA256.txt').write_text(h.hexdigest()+'  '+pkg.name+'\n')
print('macOS package built:',pkg)
