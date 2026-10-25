import io,json,sys,time,unittest,uuid
from unittest.mock import patch,MagicMock
from urllib.error import HTTPError,URLError
from providers import CloudEngine,CredentialStore,NoRedirect
from quiz import parse_quiz,suggest_quiz
ANSWER={'choice':'B','reason':'Товч үндэслэл.','confidence':'medium'}
PAYLOAD={'messages':[{'role':'system','content':'rules'},{'role':'user','content':'data'}],'response_format':{'schema':{'type':'object','properties':{'choice':{'type':'string'},'reason':{'type':'string'},'confidence':{'type':'string'}},'required':['choice','reason','confidence'],'additionalProperties':False}}}
class ProviderTests(unittest.TestCase):
    def request(self,provider):
        result={'candidates':[{'content':{'parts':[{'text':json.dumps(ANSWER)}]}}]} if provider=='gemini' else {'choices':[{'message':{'content':json.dumps(ANSWER)}}]}
        response=MagicMock();response.__enter__.return_value.read.return_value=json.dumps(result).encode()
        opener=MagicMock();opener.open.return_value=response
        with patch('providers.CredentialStore.get',return_value='test-secret'),patch('providers.build_opener',return_value=opener):
            content=CloudEngine(provider,'test-model').complete(PAYLOAD,time.monotonic()+20)
        self.assertEqual(json.loads(content),ANSWER)
        req=opener.open.call_args.args[0];self.assertNotIn('test-secret',req.full_url);self.assertNotIn('test-secret',req.data.decode())
        return req,json.loads(req.data)
    def test_gemini(self):
        req,body=self.request('gemini');self.assertEqual(req.get_header('X-goog-api-key'),'test-secret');self.assertIn('responseFormat',body['generationConfig']);self.assertIn('generativelanguage.googleapis.com',req.full_url)
    def test_openai(self):
        req,body=self.request('openai');self.assertEqual(req.full_url,'https://api.openai.com/v1/chat/completions');self.assertEqual(body['response_format']['type'],'json_schema');self.assertEqual(req.get_header('Authorization'),'Bearer test-secret')
    def test_grok(self):
        req,body=self.request('grok');self.assertEqual(req.full_url,'https://api.x.ai/v1/chat/completions');self.assertEqual(body['reasoning_effort'],'none')
    def test_http_error_redaction(self):
        opener=MagicMock();opener.open.side_effect=HTTPError('https://api.openai.com',401,'test-secret',{},io.BytesIO(b'test-secret'))
        with patch('providers.CredentialStore.get',return_value='test-secret'),patch('providers.build_opener',return_value=opener):
            with self.assertRaises(RuntimeError) as e:CloudEngine('openai','model').complete(PAYLOAD,time.monotonic()+2)
            self.assertNotIn('test-secret',str(e.exception));self.assertIn('түлхүүр',str(e.exception))
    def test_missing_key_no_network(self):
        with patch('providers.CredentialStore.get',return_value=None),patch('providers.build_opener') as op:
            with self.assertRaises(ValueError):CloudEngine('grok','model').complete(PAYLOAD,time.monotonic()+2)
            op.assert_not_called()
    def test_deadline(self):
        with self.assertRaises(TimeoutError):CloudEngine('openai','model').complete(PAYLOAD,time.monotonic()-1)
    def test_invalid_provider_and_model(self):
        for provider,model in [('other','m'),('openai','https://attacker.example'),('gemini','m\r\nx')]:
            with self.assertRaises(ValueError):CloudEngine(provider,model)
    def test_redirect_blocked(self):self.assertIsNone(NoRedirect().redirect_request(None,None,None,None,None,None))
    def test_vault_only_no_fallback(self):
        backend=MagicMock()
        with patch('providers.CredentialStore.backend',return_value=backend):CredentialStore.set('openai',' test-secret ');backend.set_password.assert_called_once_with('BORO AI','openai','test-secret')
        with patch('providers.CredentialStore.backend',side_effect=Exception('secret-error')):
            with self.assertRaises(RuntimeError) as e:CredentialStore.set('openai','test-secret')
            self.assertNotIn('secret',str(e.exception))
    def test_cloud_quiz_validation(self):
        client=CloudEngine('openai','model');q=parse_quiz('2 + 2 хэд вэ?\nA. 3\nB. 4\nC. 5\nD. 6')
        with patch.object(client,'complete',return_value=json.dumps(ANSWER)):
            self.assertIn('Хариулт: B',suggest_quiz(q,client,[],time.monotonic()+20))
    @unittest.skipUnless(sys.platform=='win32','Windows Credential Manager')
    def test_windows_vault_roundtrip(self):
        backend=CredentialStore.backend();service='BORO test '+str(uuid.uuid4())
        try:
            backend.set_password(service,'fixture','not-a-real-key');self.assertEqual(backend.get_password(service,'fixture'),'not-a-real-key')
        finally:
            if backend.get_password(service,'fixture'):backend.delete_password(service,'fixture')
