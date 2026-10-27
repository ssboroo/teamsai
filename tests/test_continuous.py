import json, tempfile, types, unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from history import AnswerHistory
from ocr import configure_subprocess

class ContinuousTests(unittest.TestCase):
    def test_windows_probes_and_ocr_are_hidden_without_global_patch(self):
        base=types.SimpleNamespace(run=MagicMock(),check_output=MagicMock(),Popen=MagicMock())
        module=types.SimpleNamespace(subprocess=base)
        with patch('ocr.sys.platform','win32'),patch('ocr.subprocess.CREATE_NO_WINDOW',0x08000000,create=True):
            configure_subprocess(module);configured=module.subprocess;configure_subprocess(module)
            self.assertIs(module.subprocess,configured)
            for name in ('run','check_output','Popen'):
                getattr(module.subprocess,name)(['tesseract'],creationflags=4)
                self.assertEqual(getattr(base,name).call_args.kwargs['creationflags'],0x08000004)
            self.assertIsNot(module.subprocess,base)
    def test_history_survives_restart_and_bounds_size(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'answers.json';h=AnswerHistory(path,2)
            for i in range(3):h.add(str(i),'Хариулт: B',[],1.2)
            loaded=AnswerHistory(path,2)
            self.assertEqual([r['question'] for r in loaded.items],['1','2'])
            self.assertFalse(h.save_error)
            self.assertFalse(path.with_suffix('.tmp').exists())
    def test_corrupt_history_and_write_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'answers.json';path.write_text('{broken')
            h=AnswerHistory(path);self.assertEqual(h.items,[])
            with patch.object(Path,'write_text',side_effect=OSError):h.add('асуулт','хариу',[],1)
            self.assertTrue(h.save_error);self.assertEqual(len(h.items),1)

class PipelineTests(unittest.TestCase):
    def app(self):
        import queue
        from app import App
        from core import Deduper
        a=App.__new__(App)
        a.q=queue.Queue();a.root=MagicMock();a.status=MagicMock();a.choice=MagicMock();a.question=MagicMock();a.answer=MagicMock()
        a.busy=False;a.answer_busy=False;a.running=True;a.generation=1;a.last='';a.started=0;a.candidate_started=0
        a.dedup=Deduper();a.failures={};a.results={};a.history=MagicMock();a.history.save_error=False
        a.refresh_history=MagicMock();a.display_answer=MagicMock();a.audit=MagicMock();a.worker=MagicMock()
        a.general=MagicMock();a.general.get.return_value=True;a.provider=MagicMock();a.provider.get.return_value='local';a.engine=object()
        return a
    def test_new_question_ocr_continues_during_inference(self):
        a=self.app();a.answer_busy=True
        q='Монгол Улсын нийслэл?\nA. Дархан\nB. Улаанбаатар\nC. Эрдэнэт\nD. Ховд'
        for _ in range(2):a.q.put(('ocr',(q,95,.1),1));a.drain()
        self.assertEqual(a.last,q);a.worker.assert_not_called();self.assertTrue(a.answer_busy)
        a.q.put(('answer',('Хариулт: A',[],'old-key',4,'Хуучин асуулт'),1));a.drain()
        a.history.add.assert_called_once();a.display_answer.assert_not_called();self.assertFalse(a.answer_busy)
        a.q.put(('ocr',(q,95,.1),1));a.drain()
        self.assertEqual(a.worker.call_args.args[0],'answer')
    def test_error_retries_and_does_not_stop_monitor(self):
        a=self.app();a.answer_busy=True;a.busy=True
        a.q.put(('error',('answer','TimeoutError','timeout'),1));a.drain()
        self.assertTrue(a.running);self.assertTrue(a.busy);self.assertFalse(a.answer_busy)
        self.assertEqual(a.candidate_started,0);a.root.after.assert_called()
    def test_stop_discards_inflight_result(self):
        a=self.app();a.running=False;a.generation=2
        a.q.put(('answer',('Хариулт: A',[],'key',4,'question'),1));a.drain()
        a.history.add.assert_not_called();a.display_answer.assert_not_called()

    def test_pending_question_starts_without_another_capture(self):
        a=self.app();a.answer_busy=True
        q='Монгол Улсын нийслэл?\nA. Дархан\nB. Улаанбаатар\nC. Эрдэнэт\nD. Ховд'
        for _ in range(2):a.q.put(('ocr',(q,95,.1),1));a.drain()
        a.q.put(('answer',('Хариулт: A',[],'old-key',4,'Хуучин асуулт'),1));a.drain()
        a.worker.assert_called_once()
        self.assertEqual(a.active_question,q)

    def test_incomplete_ocr_does_not_erase_previous_answer(self):
        a=self.app()
        a.q.put(('ocr',('???',90,.1),1));a.drain()
        a.answer.delete.assert_not_called()
        a.worker.assert_not_called()

    def test_open_question_starts_after_two_stable_reads(self):
        a=self.app()
        for _ in range(2):a.q.put(('ocr',('Монгол Улсын нийслэл юу вэ?',62,.1),1));a.drain()
        a.worker.assert_called_once()
        self.assertEqual(a.active_question,'Монгол Улсын нийслэл юу вэ?')

    def test_manual_answer_is_shown_while_monitor_stopped(self):
        a=self.app();a.running=False;a.last='Монгол Улсын нийслэл?'
        a.q.put(('manual_answer',('Хариулт: Улаанбаатар',[],'manual-key',2,a.last),1));a.drain()
        a.history.add.assert_called_once();a.display_answer.assert_called_once()
        a.worker.assert_not_called()
