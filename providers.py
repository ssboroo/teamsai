"""Opt-in cloud adapters. Fixed HTTPS hosts, OS-only credential storage, no secret logs."""
import copy,json,re,sys,time
from urllib.request import Request,build_opener,ProxyHandler,HTTPRedirectHandler
from urllib.error import HTTPError,URLError

PROVIDERS={'local':'Локал (офлайн)','gemini':'Gemini','openai':'OpenAI','grok':'Grok / xAI'}
DEFAULT_MODELS={'gemini':'gemini-3.8-flash','openai':'gpt-4.1-mini','grok':'grok-4.3'}

class CredentialStore:
    @staticmethod
    def backend():
        if sys.platform=='win32':
            from keyring.backends.Windows import WinVaultKeyring
            return WinVaultKeyring()
        if sys.platform=='darwin':
            from keyring.backends.macOS import Keyring
            return Keyring()
        raise RuntimeError('Түлхүүрийг зөвхөн Windows Credential Manager эсвэл macOS Keychain-д хадгална.')
    @classmethod
    def get(cls,provider):
        try:
            key=cls.backend().get_password('BORO AI',provider)
            if key is not None and (not isinstance(key,str) or not re.fullmatch(r'[\x21-\x7e]{1,2000}',key)):raise ValueError('invalid')
            return key
        except Exception:raise RuntimeError('OS-ийн түлхүүрийн сан нээгдсэнгүй. Credential Manager / Keychain-аа шалгана уу.') from None
    @classmethod
    def set(cls,provider,key):
        if provider not in DEFAULT_MODELS:raise ValueError('AI үйлчилгээ буруу')
        key=key.strip()
        if not re.fullmatch(r'[\x21-\x7e]{1,2000}',key):raise ValueError('API түлхүүрийн хэлбэр буруу')
        try:cls.backend().set_password('BORO AI',provider,key)
        except Exception:raise RuntimeError('OS-ийн түлхүүрийн санд хадгалж чадсангүй. Энгийн файлд хадгалахгүй.') from None
    @classmethod
    def delete(cls,provider):
        try:
            backend=cls.backend()
            if backend.get_password('BORO AI',provider):backend.delete_password('BORO AI',provider)
        except Exception:raise RuntimeError('Хадгалсан түлхүүрийг устгаж чадсангүй.') from None

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

class CloudEngine:
    def __init__(self,provider,model):
        if provider not in DEFAULT_MODELS:raise ValueError('AI үйлчилгээ буруу')
        if not isinstance(model,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,120}',model):raise ValueError('Моделийн нэр буруу')
        self.provider=provider;self.model=model
    def complete(self,payload,deadline):
        remaining=deadline-time.monotonic()
        if remaining<1:raise TimeoutError('30 секундийн төсөв дууссан байна.')
        key=CredentialStore.get(self.provider)
        if not key:raise ValueError('Settings-д API түлхүүрээ хадгална уу.')
        schema=copy.deepcopy(payload['response_format']['schema'])
        schema['properties']['reason']={'type':'string'}
        headers={'Content-Type':'application/json'}
        if self.provider=='gemini':
            url=f'https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent'
            headers['x-goog-api-key']=key
            body={'systemInstruction':{'parts':[{'text':payload['messages'][0]['content']}]},'contents':[{'role':'user','parts':[{'text':payload['messages'][1]['content']}]}],'generationConfig':{'temperature':0,'maxOutputTokens':320,'responseFormat':{'text':{'mimeType':'APPLICATION_JSON','schema':schema}}}}
        else:
            url='https://api.openai.com/v1/chat/completions' if self.provider=='openai' else 'https://api.x.ai/v1/chat/completions'
            headers['Authorization']='Bearer '+key
            body={'model':self.model,'messages':payload['messages'],'stream':False,'response_format':{'type':'json_schema','json_schema':{'name':'boro_quiz','strict':True,'schema':schema}}}
            if self.provider=='openai':body['max_completion_tokens']=320
            else:body.update(max_tokens=320,reasoning_effort='none')
        remaining=deadline-time.monotonic()
        if remaining<1:raise TimeoutError('Түлхүүр уншихад хугацаа дууслаа; API хүсэлт илгээсэнгүй.')
        req=Request(url,data=json.dumps(body).encode(),headers=headers)
        try:
            with build_opener(ProxyHandler({}),NoRedirect()).open(req,timeout=remaining) as response:raw=response.read(200001)
        except HTTPError as exc:
            messages={401:'API түлхүүр хүчингүй.',403:'Энэ модель/үйлчилгээнд эрх хүрэхгүй.',404:'Моделийн нэр эсвэл хандалтаа шалгана уу.',429:'API лимит эсвэл кредит хүрэлцэхгүй. Локал горимыг сонгож болно.'}
            raise RuntimeError(messages.get(exc.code,f'AI үйлчилгээ HTTP {exc.code} алдаа буцаалаа.')) from None
        except (TimeoutError,URLError,OSError):raise RuntimeError('AI үйлчилгээтэй холбогдсонгүй эсвэл хугацаа хэтэрлээ.') from None
        if len(raw)>200000:raise ValueError('AI хариу хэт том')
        if time.monotonic()>deadline:raise TimeoutError('AI хариу хугацаанаас хоцорсон тул харуулахгүй.')
        try:
            result=json.loads(raw)
            if self.provider=='gemini':
                content=''.join(p.get('text','') for p in result['candidates'][0]['content']['parts'] if not p.get('thought'))
            else:content=result['choices'][0]['message']['content']
            if not isinstance(content,str):raise ValueError()
            return content
        except (KeyError,IndexError,TypeError,ValueError):raise ValueError('AI хариу дутуу, хаагдсан эсвэл бүтэц нь буруу байна.') from None
