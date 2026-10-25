"""Synthetic benchmark; not real Teams/knowledge-domain validation."""
import json,os,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image,ImageDraw,ImageFont
from runtime import Engine,tesseract
from ocr import recognize
from quiz import parse_quiz,suggest_quiz
cases=[('2 + 2 хэд вэ?\nA. 3\nB. 4\nC. 5\nD. 6','B'),('Монгол Улсын нийслэл аль вэ?\nA. Дархан\nB. Улаанбаатар\nC. Эрдэнэт\nD. Ховд','B')]
engine=Engine();rows=[]
try:
    engine.start()
    font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf' if sys.platform=='darwin' else 'C:/Windows/Fonts/arial.ttf',32)
    for text,expected in cases:
        image=Image.new('RGB',(1400,330),'white');ImageDraw.Draw(image).multiline_text((20,20),text,font=font,fill='black',spacing=10)
        start=time.monotonic();row={'expected':expected}
        try:
            first,conf=recognize(image,tesseract(),quiz_mode=True);time.sleep(3)
            second,conf2=recognize(image,tesseract(),quiz_mode=True);row['synthetic_ocr_text']=second;q=parse_quiz(second)
            if parse_quiz(first).text!=q.text:raise ValueError('OCR unstable')
            answer=suggest_quiz(q,engine,[],start+30)
            row.update(correct=('Хариулт: '+expected+' —') in answer,ocr_confidence=min(conf,conf2))
        except Exception as exc:row.update(correct=False,error=type(exc).__name__,detail=str(exc)[:240])
        row['seconds']=round(time.monotonic()-start,3);row['within_30s']=row['seconds']<30;rows.append(row)
finally:engine.stop()
report={'scope':'Synthetic rendered text, warm loaded model, two OCR passes plus 3s stability interval; no real Teams screen detection; 2 examples only.','cases':rows,'all_correct_and_under_30s':all(r['correct'] and r['within_30s'] for r in rows)}
out=Path('benchmark-results.json');out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False))
