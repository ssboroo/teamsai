import time, sys, subprocess
from functools import lru_cache

class QuietSubprocess:
    """A pytesseract-only facade: do not monkeypatch Python's subprocess module."""
    _boro_hidden=True
    def __init__(self,base):self.base=base
    def __getattr__(self,name):
        original=getattr(self.base,name)
        if name not in ('run','check_output','Popen'):return original
        def hidden(*args,**kwargs):
            kwargs['creationflags']=kwargs.get('creationflags',0) | subprocess.CREATE_NO_WINDOW
            if hasattr(subprocess,'STARTUPINFO'):
                startup=kwargs.get('startupinfo') or subprocess.STARTUPINFO()
                startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startup.wShowWindow=subprocess.SW_HIDE
                kwargs['startupinfo']=startup
            return original(*args,**kwargs)
        return hidden

def configure_subprocess(module):
    if sys.platform=='win32' and getattr(module,'subprocess',None) is not None and not getattr(module.subprocess,'_boro_hidden',False):
        module.subprocess=QuietSubprocess(module.subprocess)

@lru_cache(maxsize=8)
def languages(command, reader):
    return reader(config="")

from PIL import ImageOps, ImageFilter

def recognize(image, command, budget=10, quiz_mode=False):
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd=command
    configure_subprocess(pytesseract.pytesseract)
    try:langs=languages(command,pytesseract.get_languages)
    except (OSError,RuntimeError) as exc:
        raise RuntimeError('OCR хөдөлгүүр эхэлсэнгүй. Бүрэн BORO суулгагчаар дахин суулгана уу.') from exc
    if not {'mon','eng'}.issubset(langs): raise RuntimeError('Tesseract mon + eng traineddata суулгаагүй байна.')
    started=time.monotonic(); best=('',0,[])
    def quality(result):
        complete=True
        if quiz_mode:
            from quiz import parse_quiz
            try:parse_quiz(result[0])
            except ValueError:complete=False
        return complete,result[1]
    # First pass preserves light/dark UI; second pass boosts small Cyrillic glyphs.
    # Bound full-screen work; prepare fallback only if the fast pass fails.
    image=image.copy()
    image.thumbnail((3200,3200))
    def variants():
        # Normalize dark UI before the first pass, not only after a failure.
        from PIL import ImageStat
        if ImageStat.Stat(image.convert('L').resize((32,32))).median[0]<128:
            primary=ImageOps.invert(ImageOps.autocontrast(ImageOps.grayscale(image)))
        else:primary=image
        yield primary,6
        gray=ImageOps.autocontrast(ImageOps.grayscale(image))
        if gray.resize((1,1)).getpixel((0,0))<128:gray=ImageOps.invert(gray)
        scale=min(2.5,3600/max(image.size))
        enlarged=gray.resize((max(1,int(image.width*scale)),max(1,int(image.height*scale)))).filter(ImageFilter.SHARPEN)
        yield enlarged,11
        yield enlarged,6
        yield enlarged.point(lambda p:255 if p>160 else 0),3
    for attempt,(im,psm) in enumerate(variants()):
        remaining=budget-(time.monotonic()-started)
        if remaining<.3: break
        try:
            d=pytesseract.image_to_data(im,lang='mon+eng',config=f'--oem 1 --psm {psm}',output_type=pytesseract.Output.DICT,timeout=max(.3,remaining/(4-attempt)))
        except RuntimeError as exc:
            if 'timeout' not in str(exc).lower():raise
            continue
        lines={}; conf=[]; boxes=[]
        for i,w in enumerate(d['text']):
            c=float(d['conf'][i])
            if not w.strip() or c<0: continue
            k=(d['block_num'][i],d['par_num'][i],d['line_num'][i]); lines.setdefault(k,[]).append(w)
            conf.append(c); boxes.append((d['left'][i],d['top'][i],d['width'][i],d['height'][i]))
        result=('\n'.join(' '.join(v) for v in lines.values()),sum(conf)/max(1,len(conf)),boxes)
        if quality(result)>quality(best): best=result
        if best[1]>=80 and quality(best)[0]: break
    if not best[0]:raise RuntimeError('Зураг дээрээс бичиг уншиж чадсангүй. Асуулт харагдаж байгаа эсэхийг шалгана уу. Уншсан текстийг засах товчоор текст оруулж бас болно.')
    return best[:2]

def detect_poll(image, command):
    """Heuristic candidate region from OCR anchors, never an automatic action target."""
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd=command
    configure_subprocess(pytesseract.pytesseract)
    d=pytesseract.image_to_data(image,lang='mon+eng',config='--oem 1 --psm 11',output_type=pytesseract.Output.DICT,timeout=4)
    anchors=('poll','санал','асуулт','vote','submit','илгээх')
    hits=[i for i,w in enumerate(d['text']) if any(a in w.casefold() for a in anchors) and float(d['conf'][i])>=40]
    if not hits: raise RuntimeError('Poll хэсэг олдсонгүй. Хэсгийг гараар сонгоно уу.')
    xs=[d['left'][i] for i in hits]; ys=[d['top'][i] for i in hits]
    return (max(0,min(xs)-100),max(0,min(ys)-80),min(image.width,max(xs)+650),min(image.height,max(ys)+550))
