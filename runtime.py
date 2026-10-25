"""Own a private authenticated loopback llama-server; never uses an existing service."""
import json, os, secrets, socket, subprocess, sys, time, threading
from pathlib import Path
from urllib.request import Request, build_opener, ProxyHandler

ROOT=(Path(sys.executable).parent.parent/'Resources' if sys.platform=='darwin' else Path(sys.executable).parent) if getattr(sys,'frozen',False) else Path(__file__).parent
class Engine:
    def __init__(self):self.process=None;self.key=secrets.token_hex(32);self.port=None;self.closed=threading.Event();self.lock=threading.Lock()
    def start(self, timeout=150):
        exe=ROOT/('assets/llama/llama-server' if sys.platform=='darwin' else 'assets/llama/llama-server.exe'); model=ROOT/'assets/model/model.gguf'
        if not exe.exists() or not model.exists():raise RuntimeError('AI бүрдэл дутуу. Бүрэн суулгагчаар дахин суулгана уу.')
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));self.port=sock.getsockname()[1]
        args=[str(exe),'-m',str(model),'--host','127.0.0.1','--port',str(self.port),'--api-key',self.key,'-c','4096','-ngl','0','--parallel','1']
        with self.lock:
            if self.closed.is_set():raise RuntimeError('Хаагдсан')
            self.process=subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),cwd=str(exe.parent))
        until=time.monotonic()+timeout
        while time.monotonic()<until:
            if self.closed.is_set():raise RuntimeError('Хаагдсан')
            if self.process.poll() is not None:raise RuntimeError('AI хөдөлгүүр эхэлсэнгүй. CPU AVX2 болон RAM шалгана уу.')
            try:
                req=Request(f'http://127.0.0.1:{self.port}/health',headers={'Authorization':'Bearer '+self.key})
                with build_opener(ProxyHandler({})).open(req,timeout=1) as r:
                    if r.status==200:return
            except OSError:pass
            time.sleep(.25)
        self.stop();raise TimeoutError('AI модель ачаалах хугацаа хэтэрлээ.')
    @property
    def endpoint(self):return f'http://127.0.0.1:{self.port}/v1/chat/completions'
    def stop(self):
        self.closed.set()
        with self.lock:process=self.process
        if process and process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=5)

def tesseract():
    os.environ['TESSDATA_PREFIX']=str(ROOT/'assets/ocr/tessdata')
    return str(ROOT/('assets/ocr/tesseract' if sys.platform=='darwin' else 'assets/ocr/tesseract.exe'))
