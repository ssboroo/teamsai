from pathlib import Path
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parents[1];out=root/'branding';out.mkdir(exist_ok=True)
im=Image.new('RGBA',(1024,1024),(0,0,0,0));d=ImageDraw.Draw(im)
d.rounded_rectangle((24,24,1000,1000),radius=240,fill='#10151f')
d.rounded_rectangle((140,140,884,884),radius=200,fill='#74ebc2')
d.rectangle((310,290,425,755),fill='#10151f');d.rounded_rectangle((380,290,710,540),radius=125,fill='#10151f');d.rounded_rectangle((380,490,750,755),radius=130,fill='#10151f');d.rounded_rectangle((423,385,600,455),radius=35,fill='#74ebc2');d.rounded_rectangle((423,585,630,660),radius=36,fill='#74ebc2');d.ellipse((720,160,876,316),fill='#10151f');d.line((754,235,787,266,844,203),fill='#74ebc2',width=18)
d.rectangle((420,455,500,584),fill='#10151f')
im.save(out/'boro.png');im.save(out/'boro.ico',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)]);im.save(out/'boro.icns')
