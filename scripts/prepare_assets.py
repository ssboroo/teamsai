"""Build-time only. Downloads are never performed on the user's computer."""
import hashlib,json,os,shutil,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ASSETS=ROOT/'assets';ASSETS.mkdir(exist_ok=True);records=[]
def get(url,path,expected=None):
    path.parent.mkdir(parents=True,exist_ok=True)
    req=urllib.request.Request(url,headers={'User-Agent':'TeamsAI-build'})
    digest=hashlib.sha256()
    with urllib.request.urlopen(req,timeout=120) as r,path.open('wb') as f:
        while chunk:=r.read(1024*1024):f.write(chunk);digest.update(chunk)
    actual=digest.hexdigest()
    if expected and actual!=expected:raise RuntimeError('SHA256 mismatch: '+path.name)
    records.append(dict(file=str(path.relative_to(ROOT)),url=url,sha256=actual,bytes=path.stat().st_size))
    return path

def api(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'TeamsAI-build'}),timeout=60) as r:return json.load(r)
release=api('https://api.github.com/repos/ggml-org/llama.cpp/releases/latest')
asset=next(a for a in release['assets'] if a['name'].endswith('-bin-win-cpu-x64.zip'))
expected=(asset.get('digest') or '').removeprefix('sha256:') or None
archive=get(asset['browser_download_url'],ASSETS/'llama.zip',expected)
with zipfile.ZipFile(archive) as z:z.extractall(ASSETS/'llama')
archive.unlink()
servers=list((ASSETS/'llama').rglob('llama-server.exe'))
if len(servers)!=1:raise RuntimeError('llama-server missing/ambiguous')
if servers[0].parent!=ASSETS/'llama':
    for f in servers[0].parent.iterdir():
        if f.is_file():shutil.copy2(f,ASSETS/'llama'/f.name)
info=api('https://huggingface.co/api/models/Qwen/Qwen3-4B-GGUF?blobs=true');revision=info['sha']
model=next(x for x in info['siblings'] if x['rfilename'].lower()=='qwen3-4b-q4_k_m.gguf')
get(f'https://huggingface.co/Qwen/Qwen3-4B-GGUF/resolve/{revision}/'+model['rfilename'],ASSETS/'model/model.gguf',model.get('lfs',{}).get('sha256'))
ocr=Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Tesseract-OCR'
if not (ocr/'tesseract.exe').exists():raise RuntimeError('Build agent Tesseract missing')
shutil.copytree(ocr,ASSETS/'ocr',dirs_exist_ok=True)
tess_revision=api('https://api.github.com/repos/tesseract-ocr/tessdata_fast/commits/main')['sha']
for lang in ['mon','eng']:
    get(f'https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/{tess_revision}/{lang}.traineddata',ASSETS/f'ocr/tessdata/{lang}.traineddata')
# CPU binaries may depend on the VC runtime. Ship the redistributable DLLs app-locally.
for dll in ['vcruntime140.dll','vcruntime140_1.dll','msvcp140.dll']:
    source=Path(os.environ['WINDIR'])/'System32'/dll
    if not source.exists():raise RuntimeError('Missing VC runtime '+dll)
    for folder in ['llama','ocr']:shutil.copy2(source,ASSETS/folder/dll)
for name,url in {
 'llama-LICENSE.txt':'https://raw.githubusercontent.com/ggml-org/llama.cpp/'+release['tag_name']+'/LICENSE',
 'Qwen-LICENSE.txt':f'https://huggingface.co/Qwen/Qwen3-4B-GGUF/resolve/{revision}/LICENSE',
 'Tesseract-LICENSE.txt':'https://raw.githubusercontent.com/tesseract-ocr/tesseract/main/LICENSE',
 'tessdata-LICENSE.txt':f'https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/{tess_revision}/LICENSE'
}.items():get(url,ASSETS/'licenses'/name)
(ASSETS/'manifest.json').write_text(json.dumps({'llama_release':release['tag_name'],'model_revision':revision,'files':records},indent=2))
print('Assets prepared, hashes recorded')
