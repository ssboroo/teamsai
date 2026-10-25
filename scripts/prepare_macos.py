"""Build-only macOS assets with app-local OCR dylibs."""
import hashlib,json,os,platform,shutil,subprocess,tarfile,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];A=ROOT/'assets';A.mkdir(exist_ok=True);manifest=[]
def api(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'TeamsAI-build'}),timeout=120) as r:return json.load(r)
def download(url,path,expected=None):
    path.parent.mkdir(parents=True,exist_ok=True);h=hashlib.sha256()
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'TeamsAI-build'}),timeout=180) as r,path.open('wb') as f:
        while chunk:=r.read(1024*1024):f.write(chunk);h.update(chunk)
    if expected and h.hexdigest()!=expected:raise RuntimeError('SHA mismatch '+path.name)
    manifest.append(dict(file=str(path.relative_to(ROOT)),sha256=h.hexdigest(),url=url))
arch='arm64' if platform.machine()=='arm64' else 'x64'
r=api('https://api.github.com/repos/ggml-org/llama.cpp/releases/tags/b11871')
asset=next(a for a in r['assets'] if a['name'].endswith(f'-bin-macos-{arch}.tar.gz'))
archive=A/'llama.tar.gz';download(asset['browser_download_url'],archive,(asset.get('digest') or '').removeprefix('sha256:') or None)
with tarfile.open(archive) as tar:tar.extractall(A/'llama',filter='data')
archive.unlink();servers=list((A/'llama').rglob('llama-server'))
if len(servers)!=1:raise RuntimeError('llama-server missing')
# Upstream archive bin/ and lib/ relative layout must be retained for @rpath.
base=servers[0].parent
if base!=A/'llama':
    # Keep extracted layout; runtime launches through an app-local wrapper pointing at actual bin.
    rel=servers[0].relative_to(A/'llama')
    wrapper=A/'llama/llama-server'
    wrapper.write_text('#!/bin/sh\nexec "$(dirname "$0")/'+str(rel)+'" "$@"\n');wrapper.chmod(0o755)
info=api('https://huggingface.co/api/models/Qwen/Qwen3-4B-GGUF?blobs=true');rev=info['sha']
m=next(x for x in info['siblings'] if x['rfilename'].lower()=='qwen3-4b-q4_k_m.gguf')
download(f'https://huggingface.co/Qwen/Qwen3-4B-GGUF/resolve/{rev}/'+m['rfilename'],A/'model/model.gguf',m.get('lfs',{}).get('sha256'))
prefix=Path(subprocess.check_output(['brew','--prefix','tesseract'],text=True).strip())
ocr=A/'ocr';ocr.mkdir(exist_ok=True);shutil.copy2(prefix/'bin/tesseract',ocr/'tesseract');(ocr/'tesseract').chmod(0o755)
subprocess.run(['dylibbundler','-od','-b','-x',str(ocr/'tesseract'),'-d',str(ocr/'lib'),'-p','@executable_path/lib/'],check=True)
# Ad-hoc re-sign changed binaries inside-out (not Developer ID / notarization).
for lib in (ocr/'lib').glob('*.dylib'):subprocess.run(['codesign','--force','--sign','-',str(lib)],check=True)
subprocess.run(['codesign','--force','--sign','-',str(ocr/'tesseract')],check=True)
tess=api('https://api.github.com/repos/tesseract-ocr/tessdata_fast/commits/main')['sha']
for lang in ['mon','eng']:download(f'https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/{tess}/{lang}.traineddata',ocr/f'tessdata/{lang}.traineddata')
for name,url in {
 'llama-LICENSE.txt':'https://raw.githubusercontent.com/ggml-org/llama.cpp/b11871/LICENSE',
 'Qwen-LICENSE.txt':f'https://huggingface.co/Qwen/Qwen3-4B-GGUF/resolve/{rev}/LICENSE',
 'Tesseract-LICENSE.txt':'https://raw.githubusercontent.com/tesseract-ocr/tesseract/main/LICENSE',
 'tessdata-LICENSE.txt':f'https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/{tess}/LICENSE'
}.items():download(url,A/'licenses'/name)
# Retain Homebrew dependency licenses in the distribution.
for name in subprocess.check_output(['brew','deps','--formula','tesseract'],text=True).splitlines()+['tesseract']:
    formula=Path(subprocess.check_output(['brew','--prefix',name],text=True).strip())
    dest=A/'licenses'/name;dest.mkdir(exist_ok=True)
    for p in formula.iterdir():
        if p.is_file() and any(k in p.name.upper() for k in ['LICENSE','COPYING','NOTICE']):shutil.copy2(p,dest/p.name)
(A/'manifest.json').write_text(json.dumps({'architecture':arch,'llama':'b11871','model_revision':rev,'files':manifest},indent=2))
print('macOS assets prepared:',arch)
