import sys,types,unittest
from unittest.mock import MagicMock,patch
from PIL import Image
from ocr import recognize

def data(lines,confidence):
    n=len(lines)
    return dict(text=lines,conf=[confidence]*n,block_num=[1]*n,par_num=[1]*n,line_num=list(range(n)),left=[0]*n,top=[0]*n,width=[20]*n,height=[20]*n)
class OCRStrategyTests(unittest.TestCase):
    def test_complete_options_beat_higher_average_confidence(self):
        incomplete=data(['2 + 2 хэд вэ?','A. 3','B. 4','C. 5'],95)
        complete=data(['2 + 2 хэд вэ?','A. 3','B. 4','C. 5','D. 6'],80)
        mock=types.SimpleNamespace(pytesseract=types.SimpleNamespace(),get_languages=lambda **k:['mon','eng'],Output=types.SimpleNamespace(DICT='dict'),image_to_data=MagicMock(side_effect=[incomplete,complete]))
        with patch.dict(sys.modules,{'pytesseract':mock}):
            text,confidence=recognize(Image.new('RGB',(400,300),'white'),'tesseract',quiz_mode=True)
        self.assertIn('D. 6',text);self.assertEqual(confidence,80);self.assertEqual(mock.image_to_data.call_count,2)
    def test_complete_high_confidence_stays_fast(self):
        complete=data(['2 + 2 хэд вэ?','A. 3','B. 4','C. 5','D. 6'],92)
        mock=types.SimpleNamespace(pytesseract=types.SimpleNamespace(),get_languages=lambda **k:['mon','eng'],Output=types.SimpleNamespace(DICT='dict'),image_to_data=MagicMock(return_value=complete))
        with patch.dict(sys.modules,{'pytesseract':mock}):recognize(Image.new('RGB',(400,300),'white'),'tesseract',quiz_mode=True)
        self.assertEqual(mock.image_to_data.call_count,1)
