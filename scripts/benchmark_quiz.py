"""Synthetic benchmark; not real Teams/knowledge-domain validation."""
import json,os,sys,time,platform
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image,ImageDraw,ImageFont
from runtime import Engine,tesseract
from ocr import recognize
from quiz import parse_quiz
from reading import readable_text,answer_question
cases=[('2 + 2 хэд вэ?\nA. 3\nB. 4\nC. 5\nD. 6','B'),('Монгол Улсын нийслэл аль вэ?\nA. Дархан\nB. Улаанбаатар\nC. Эрдэнэт\nD. Ховд','B')]
cases += [('Монгол Улсын нийслэл юу вэ?','Улаанбаатар'),('Монгол Улсын нийслэл аль вэ?\n1. Дархан\n2. Улаанбаатар','Улаанбаатар')]
engine=Engine();rows=[]
try:
    engine.start()
    font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf' if sys.platform=='darwin' else 'C:/Windows/Fonts/arial.ttf',32)
    for text,expected in cases:
      for theme in ('light','dark'):
        image=Image.new('RGB',(1400,330),'white' if theme=='light' else '#151b27');ImageDraw.Draw(image).multiline_text((20,20),text,font=font,fill='black' if theme=='light' else 'white',spacing=10)
        start=time.monotonic();row={'expected':expected,'theme':theme}
        try:
            first,conf=recognize(image,tesseract(),budget=6,quiz_mode=True);time.sleep(.2)
            second,conf2=recognize(image,tesseract(),budget=6,quiz_mode=True);row['synthetic_ocr_text']=second;q=readable_text(second)
            if readable_text(first)!=q:raise ValueError('OCR unstable')
            row['ocr_seconds']=round(time.monotonic()-start,3)
            ai_start=time.monotonic()
            answer=answer_question(q,engine,[],ai_start+30)
            row['ai_seconds']=round(time.monotonic()-ai_start,3)
            row.update(correct=(('Хариулт: '+expected+' —') in answer if expected=='B' else expected.casefold() in answer.casefold()),ocr_confidence=min(conf,conf2),answer=answer)
            row['ocr_exact']= ''.join(q.split()).casefold()==''.join(readable_text(text).split()).casefold()
        except Exception as exc:row.update(correct=False,error=type(exc).__name__,detail=str(exc)[:240])
        row['seconds']=round(time.monotonic()-start,3);row['within_10s']=row['seconds']<10;row['within_30s']=row['seconds']<30;rows.append(row)
finally:engine.stop()
report={'platform':platform.platform(),'processor':platform.processor(),'scope':'Synthetic rendered text, warm loaded model, two OCR passes plus 0.2s scheduling interval; no real Teams screen detection; 4 questions (quiz, open and numbered options) in light/dark themes; not representative accuracy evidence.','cases':rows,'all_correct_and_under_10s':all(r['correct'] and r['within_10s'] for r in rows),'all_correct_and_under_30s':all(r['correct'] and r['within_30s'] for r in rows)}
out=Path('benchmark-results.json');out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False))
