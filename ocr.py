import time
from PIL import ImageOps, ImageFilter

def recognize(image, command, budget=6):
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd=command
    langs=pytesseract.get_languages(config='')
    if not {'mon','eng'}.issubset(langs): raise RuntimeError('Tesseract mon + eng traineddata суулгаагүй байна.')
    started=time.monotonic(); best=('',0,[])
    # First pass preserves light/dark UI; second pass boosts small Cyrillic glyphs.
    gray=ImageOps.grayscale(image)
    variants=[(image,6),(ImageOps.autocontrast(gray).resize((image.width*2,image.height*2)).filter(ImageFilter.SHARPEN),6)]
    for im,psm in variants:
        remaining=budget-(time.monotonic()-started)
        if remaining<.3: break
        try:
            d=pytesseract.image_to_data(im,lang='mon+eng',config=f'--oem 1 --psm {psm}',output_type=pytesseract.Output.DICT,timeout=remaining)
        except RuntimeError:
            if best[0]: break
            raise
        lines={}; conf=[]; boxes=[]
        for i,w in enumerate(d['text']):
            c=float(d['conf'][i])
            if not w.strip() or c<0: continue
            k=(d['block_num'][i],d['par_num'][i],d['line_num'][i]); lines.setdefault(k,[]).append(w)
            conf.append(c); boxes.append((d['left'][i],d['top'][i],d['width'][i],d['height'][i]))
        result=('\n'.join(' '.join(v) for v in lines.values()),sum(conf)/max(1,len(conf)),boxes)
        if result[1]>best[1]: best=result
        if best[1]>=85: break
    return best[:2]

def detect_poll(image, command):
    """Heuristic candidate region from OCR anchors, never an automatic action target."""
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd=command
    d=pytesseract.image_to_data(image,lang='mon+eng',config='--oem 1 --psm 11',output_type=pytesseract.Output.DICT,timeout=4)
    anchors=('poll','санал','асуулт','vote','submit','илгээх')
    hits=[i for i,w in enumerate(d['text']) if any(a in w.casefold() for a in anchors) and float(d['conf'][i])>=40]
    if not hits: raise RuntimeError('Poll хэсэг олдсонгүй. Хэсгийг гараар сонгоно уу.')
    xs=[d['left'][i] for i in hits]; ys=[d['top'][i] for i in hits]
    return (max(0,min(xs)-100),max(0,min(ys)-80),min(image.width,max(xs)+650),min(image.height,max(ys)+550))
