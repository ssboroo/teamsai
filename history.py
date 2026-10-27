"""Bounded local question/answer history; never stores images or credentials."""
import json
from datetime import datetime
from pathlib import Path

class AnswerHistory:
    def __init__(self,path,limit=200):
        self.path=Path(path);self.limit=limit;self.items=[];self.save_error=False
        try:
            rows=json.loads(self.path.read_text(encoding='utf-8'))
            if isinstance(rows,list):
                self.items=[r for r in rows if isinstance(r,dict) and all(isinstance(r.get(k),str) for k in ('question','answer','time')) and isinstance(r.get('refs'),list) and all(isinstance(x,dict) for x in r['refs']) and isinstance(r.get('elapsed'),(int,float))][-limit:]
        except (OSError,ValueError):pass
    def add(self,question,answer,refs,elapsed):
        self.items.append(dict(question=question,answer=answer,refs=refs,elapsed=elapsed,time=datetime.now().strftime('%m-%d %H:%M:%S')))
        self.items=self.items[-self.limit:]
        temporary=self.path.with_suffix('.tmp')
        try:
            temporary.write_text(json.dumps(self.items,ensure_ascii=False),encoding='utf-8')
            temporary.replace(self.path);self.save_error=False
        except OSError:self.save_error=True
