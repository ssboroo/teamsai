"""Real Tesseract regression gate on rendered Mongolian quiz layouts."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image,ImageDraw,ImageFont
from runtime import tesseract
from ocr import recognize
from quiz import parse_quiz
font_path='C:/Windows/Fonts/arial.ttf' if sys.platform=='win32' else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
rows=[]
for size,dark,labels in [(20,False,'ABCD'),(20,True,'ABCD'),(30,False,'АБВГ'),(30,True,'АБВГ'),(24,False,'1234'),(24,True,'1234')]:
    font=ImageFont.truetype(font_path,size)
    im=Image.new('RGB',(900,300),'#171c28' if dark else 'white');d=ImageDraw.Draw(im)
    lines=['Монгол Улсын нийслэл аль вэ?']+[label+'. '+option for label,option in zip(labels,['Дархан','Улаанбаатар','Эрдэнэт','Ховд'])]
    d.multiline_text((30,25),'\n'.join(lines),font=font,fill='white' if dark else 'black',spacing=12)
    text,confidence=recognize(im,tesseract(),budget=15,quiz_mode=True)
    try:
        q=parse_quiz(text)
        assert 'улаанбаатар' in q.options['B'].casefold(),q.options
        assert confidence>=70,confidence
    except Exception:
        print(repr(text));raise
    rows.append(dict(font_size=size,dark=dark,labels=labels,confidence=round(confidence,1)))
print(json.dumps(rows,ensure_ascii=False))
