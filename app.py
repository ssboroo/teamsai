import ctypes, json, os, queue, sys, threading, time, tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from core import clean, Deduper, LawIndex, local_chat
from runtime import Engine, ROOT, tesseract
DATA=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'TeamsAI';DATA.mkdir(parents=True,exist_ok=True);(DATA/'laws').mkdir(exist_ok=True)
BG='#10151f';CARD='#1b2331';FG='#ecf2ff';MUTED='#a6b5cc';ACCENT='#74ebc2'
class App:
    def __init__(self,root):
        self.root=root;self.engine=Engine();self.q=queue.Queue();self.ready=False;self.busy=False;self.running=False;self.region=None;self.last='';self.dedup=Deduper();self.failures={};self.generation=0;self.started=0
        root.title('TeamsAI • Дэлгэцийн туслах');root.geometry('460x680');root.minsize(420,560);root.configure(bg=BG)
        try:self.settings=json.loads((DATA/'settings.json').read_text())
        except (OSError,ValueError):self.settings={}
        self.interval=tk.IntVar(value=max(1,min(30,int(self.settings.get('interval',3)))));self.general=tk.BooleanVar(value=True)
        self.label('TEAMS AI',24,ACCENT).pack(anchor='w',padx=22,pady=(22,2));self.label('Дэлгэц уншина. Хариу санал болгоно.',10,MUTED).pack(anchor='w',padx=22)
        controls=tk.Frame(root,bg=BG);controls.pack(fill='x',padx=22,pady=18)
        self.button(controls,'① Хэсэг сонгох',self.select).pack(side='left',fill='x',expand=True,padx=(0,8))
        self.start_button=self.button(controls,'▶ Эхлэх',self.toggle);self.start_button.pack(side='left',fill='x',expand=True)
        self.status=tk.StringVar(value='AI модель ачаалж байна… Эхний удаа удаж болно.')
        tk.Label(root,textvariable=self.status,bg=CARD,fg=ACCENT,wraplength=400,justify='left',padx=12,pady=10,font=('Segoe UI',10)).pack(fill='x',padx=22)
        self.label('ДЭЛГЭЦЭЭС УНШСАН АСУУЛТ',9,MUTED).pack(anchor='w',padx=22,pady=(16,6))
        self.question=self.text(5);self.question.pack(fill='x',padx=22)
        self.label('ХАРИУЛТЫН САНАЛ',9,MUTED).pack(anchor='w',padx=22,pady=(16,6))
        self.answer=self.text(10);self.answer.pack(fill='both',expand=True,padx=22)
        footer=tk.Frame(root,bg=BG);footer.pack(fill='x',padx=22,pady=12)
        self.button(footer,'Хуулах',self.copy).pack(side='left');self.button(footer,'Тохиргоо',self.options).pack(side='right')
        self.label('Локал • API түлхүүргүй • Teams-д өөрөө илгээнэ',9,MUTED).pack(pady=(0,12))
        root.after(100,self.drain);root.protocol('WM_DELETE_WINDOW',self.close)
        self.worker('ready',lambda:self.engine.start())
    def label(self,text,size=11,color=FG):return tk.Label(self.root,text=text,bg=BG,fg=color,font=('Segoe UI',size,'bold' if size>15 else 'normal'))
    def text(self,height):return tk.Text(self.root,height=height,bg=CARD,fg=FG,insertbackground=FG,relief='flat',wrap='word',font=('Segoe UI',11),padx=10,pady=10)
    def button(self,parent,text,fn):return tk.Button(parent,text=text,command=fn,bg=CARD,fg=FG,activebackground='#2d4057',activeforeground=FG,relief='flat',padx=12,pady=10,font=('Segoe UI',10),cursor='hand2')
    def audit(self,event,**data):
        try:
            p=DATA/'audit.jsonl'
            if p.exists() and p.stat().st_size>2_000_000:p.replace(DATA/'audit.previous.jsonl')
            with p.open('a',encoding='utf-8') as f:f.write(json.dumps(dict(time=time.time(),event=event,**data))+'\n')
        except OSError:pass
    def worker(self,tag,fn,epoch=None):
        self.busy=True
        def run():
            try:self.q.put((tag,fn(),epoch))
            except Exception as e:self.q.put(('error',(tag,type(e).__name__,str(e)[:250]),epoch))
        threading.Thread(target=run,daemon=True).start()
    def drain(self):
        try:
            tag,value,epoch=self.q.get_nowait();self.busy=False
            if tag=='ready':self.ready=True;self.status.set('Бэлэн. Асуултын хэсгээ сонгоод Эхлэх дарна уу.')
            elif tag=='error':self.status.set('Алдаа: '+value[2]);self.audit('error',stage=value[0],kind=value[1])
            elif epoch==self.generation and self.running:
                if tag=='ocr':
                    text,confidence,elapsed=value;self.question.delete('1.0','end');self.question.insert('1.0',text)
                    self.status.set(f'OCR {confidence:.0f}% • {elapsed:.1f}с')
                    stable=text==self.last;self.last=text
                    hit,key=self.dedup.check(text)
                    if stable and confidence>=70 and len(text)>12 and not hit and time.monotonic()>self.failures.get(key,0):
                        self.failures[key]=time.monotonic()+60;self.started=time.monotonic()-elapsed
                        general=self.general.get();self.status.set('Хариу боловсруулж байна…')
                        def infer():
                            refs=LawIndex(DATA/'laws').search(text)
                            answer=local_chat('bundled',text,refs,timeout=25,allow_general=general,endpoint=self.engine.endpoint,api_key=self.engine.key)
                            return answer,refs,key,time.monotonic()-self.started
                        self.worker('answer',infer,epoch)
                    elif confidence<70:self.status.set('Текст бүдэг байна. Хэсгийг томруулж дахин сонгоно уу.')
                elif tag=='answer':
                    answer,refs,key,elapsed=value;self.dedup.seen[key]=time.monotonic()
                    self.answer.delete('1.0','end');self.answer.insert('1.0',answer+'\n\n'+'\n\n'.join(f'[{i+1}] {r["title"]} {r["article"]}\n{r["text"]}\n{r["source"]} • {r["verified_on"]}' for i,r in enumerate(refs)))
                    self.status.set(f'Санал бэлэн • OCR + AI {elapsed:.1f}с');self.audit('answer',poll_hash=key,seconds=round(elapsed,2))
        except queue.Empty:pass
        self.root.after(100,self.drain)
    def select(self):
        if self.running:self.toggle()
        top=tk.Toplevel(self.root);top.attributes('-fullscreen',True);top.attributes('-alpha',.35);top.attributes('-topmost',True)
        c=tk.Canvas(top,bg='black',cursor='crosshair');c.pack(fill='both',expand=True);start=[];rect=[]
        def down(e):start[:]=[e.x_root,e.y_root];rect[:]=[c.create_rectangle(e.x,e.y,e.x,e.y,outline=ACCENT,width=3)]
        def move(e):
            if rect:c.coords(rect[0],start[0]-top.winfo_rootx(),start[1]-top.winfo_rooty(),e.x,e.y)
        def up(e):
            if start:
                box=(min(start[0],e.x_root),min(start[1],e.y_root),max(start[0],e.x_root),max(start[1],e.y_root))
                if box[2]-box[0]>40 and box[3]-box[1]>40:self.region=box;self.status.set('Хэсэг сонголоо. Эхлэх товчийг дарна уу.')
            top.destroy()
        c.bind('<Button-1>',down);c.bind('<B1-Motion>',move);c.bind('<ButtonRelease-1>',up);top.bind('<Escape>',lambda e:top.destroy())
    def toggle(self):
        if self.running:
            self.running=False;self.generation+=1;self.start_button.config(text='▶ Эхлэх');self.status.set('Зогссон');return
        if not self.ready:self.status.set('AI модель ачаалж дуустал хүлээнэ үү.');return
        if not self.region:self.select();return
        if not messagebox.askyesno('Дэлгэц унших','Сонгосон хэсгийг локал OCR болон AI-аар давтан боловсруулж хариу харуулах уу?'):return
        self.running=True;self.generation+=1;self.last='';self.start_button.config(text='■ Зогсоох');self.tick(self.generation)
    def tick(self,epoch):
        if not self.running or epoch!=self.generation:return
        if not self.busy:
            box=self.region
            def capture():
                from PIL import ImageGrab
                from ocr import recognize
                t=time.monotonic();text,confidence=recognize(ImageGrab.grab(bbox=box),tesseract())
                return clean(text),confidence,time.monotonic()-t
            self.worker('ocr',capture,epoch)
        self.root.after(max(1,self.interval.get())*1000,lambda:self.tick(epoch))
    def copy(self):
        text=self.answer.get('1.0','end').strip()
        if text and messagebox.askyesno('Хуулах','Саналыг нягталсан уу? Clipboard-д хуулах уу?'):self.root.clipboard_clear();self.root.clipboard_append(text)
    def options(self):
        w=tk.Toplevel(self.root);w.title('Тохиргоо');w.configure(bg=BG);w.geometry('380x230')
        tk.Label(w,text='Дэлгэц унших завсар (секунд)',bg=BG,fg=FG).pack(pady=10)
        tk.Scale(w,from_=1,to=30,orient='horizontal',variable=self.interval,bg=BG,fg=FG,highlightthickness=0).pack(fill='x',padx=20)
        tk.Checkbutton(w,text='Хуулийн сангүй үед ерөнхий санал',variable=self.general,bg=BG,fg=FG,selectcolor=CARD).pack()
        self.button(w,'Хуулийн сан нэмэх',self.import_law).pack(pady=10)
    def import_law(self):
        path=filedialog.askopenfilename(filetypes=[('Хуулийн сан','*.json')])
        if not path:return
        try:
            import tempfile,shutil
            with tempfile.TemporaryDirectory() as t:
                p=Path(t)/Path(path).name;shutil.copyfile(path,p);index=LawIndex(t)
                if not index.rows:raise ValueError('Хүчинтэй заалт алга')
                if messagebox.askyesno('Хуулийн сан',f'{len(index.rows)} заалтын эх сурвалж, хүчинтэй байдлыг шалгасан уу?'):shutil.copyfile(p,DATA/'laws'/p.name)
        except Exception as e:messagebox.showerror('Алдаа',str(e))
    def close(self):
        self.running=False
        (DATA/'settings.json').write_text(json.dumps({'interval':self.interval.get()}))
        self.engine.stop();self.root.destroy()

def self_test():
    from PIL import Image,ImageDraw,ImageFont
    from ocr import recognize
    image=Image.new('RGB',(1000,200),'white');draw=ImageDraw.Draw(image)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',36)
    draw.text((20,20),'Монгол Улс Ө Ү хууль 123',font=font,fill='black')
    text,conf=recognize(image,tesseract(),budget=20)
    if 'Монгол' not in text or conf<40:raise RuntimeError('OCR smoke failed: '+text)
    engine=Engine()
    try:
        engine.start();result=local_chat('bundled','2+2 хэд вэ?',[],timeout=120,allow_general=True,endpoint=engine.endpoint,api_key=engine.key)
        if '4' not in result:raise RuntimeError('AI smoke failed')
    finally:engine.stop()
    print('Bundled OCR and AI smoke passed')
if __name__=='__main__':
    if '--self-test' in sys.argv:self_test()
    else:
        if os.name=='nt':ctypes.windll.user32.SetProcessDPIAware()
        root=tk.Tk();App(root);root.mainloop()
