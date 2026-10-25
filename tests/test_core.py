import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from core import clean, Deduper, LawIndex, local_chat
class Tests(unittest.TestCase):
    def test_cyrillic(self):self.assertEqual(clean('  Монгол   Ө Ү\n\n хууль '),'Монгол Ө Ү\nхууль')
    def test_duplicate(self):
        d=Deduper();self.assertFalse(d.check('Асуулт?')[0]);d.check('Асуулт?',True);self.assertTrue(d.check('АСУУЛТ')[0])
    def test_expiry(self):
        d=Deduper(ttl=1)
        with patch('core.time.monotonic',return_value=0):d.check('test',True)
        with patch('core.time.monotonic',return_value=2):self.assertFalse(d.check('test')[0])
    def test_law_search(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'law.json'; row={'title':'Жишээ','article':'1','text':'ажилтны хөдөлмөрийн гэрээ','source':'https://example.invalid','verified_on':'2026-10-25','status':'active'}
            p.write_text(json.dumps([row]),encoding='utf-8');self.assertEqual(len(LawIndex(t).search('хөдөлмөр')),1)
            row['status']='repealed';p.write_text(json.dumps([row]),encoding='utf-8');self.assertEqual(LawIndex(t).search('хөдөлмөр'),[])
    def test_schema(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t)/'bad.json').write_text('[{}]')
            with self.assertRaises(ValueError):LawIndex(t)
    def test_no_evidence_no_network(self):self.assertIn('Баримт хангалтгүй',local_chat('qwen3:8b','question',[]))
    def test_general_local_response(self):
        from unittest.mock import MagicMock
        response=MagicMock();response.__enter__.return_value.read.return_value=json.dumps({'message':{'content':'B сонголт'}}).encode()
        opener=MagicMock();opener.open.return_value=response
        with patch('core.build_opener',return_value=opener):
            result=local_chat('qwen3:8b','question',[],allow_general=True)
            self.assertIn('БАТАЛГААЖААГҮЙ',result)
            self.assertIn('B сонголт',result)
            self.assertEqual(opener.open.call_args.args[0].full_url,'http://127.0.0.1:11434/api/chat')
    def test_remote_endpoint_rejected(self):
        with self.assertRaises(ValueError):local_chat('bundled','question',[],allow_general=True,endpoint='https://example.com/v1/chat/completions')
    def test_private_server_auth(self):
        from unittest.mock import MagicMock
        response=MagicMock();response.__enter__.return_value.read.return_value=json.dumps({'choices':[{'message':{'content':'4'}}]}).encode()
        opener=MagicMock();opener.open.return_value=response
        with patch('core.build_opener',return_value=opener):
            result=local_chat('bundled','question',[],allow_general=True,endpoint='http://127.0.0.1:12345/v1/chat/completions',api_key='test-token')
            self.assertIn('4',result)
            req=opener.open.call_args.args[0]
            self.assertEqual(req.get_header('Authorization'),'Bearer test-token')
            self.assertFalse(json.loads(req.data)['chat_template_kwargs']['enable_thinking'])
    def test_invalid_model(self):
        with self.assertRaises(ValueError):local_chat('bad model','q',[])
if __name__=='__main__':unittest.main()
