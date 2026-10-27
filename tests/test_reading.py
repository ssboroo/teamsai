import json,time,unittest
from unittest.mock import MagicMock,patch
from reading import readable_text,answer_question

class ReadingTests(unittest.TestCase):
    def test_open_question_without_options(self):
        self.assertEqual(readable_text('Монгол Улсын нийслэл юу вэ?'),'Монгол Улсын нийслэл юу вэ?')
    def test_partial_options_preserved_without_inventing_labels(self):
        text='Монгол Улсын нийслэл?\nA. Дархан\nB. Улаанбаатар\nП. Ховд'
        self.assertEqual(readable_text(text),text)
    def test_noise_and_oversized_text_rejected(self):
        for raw in ['','???','00:21\nSubmit','а'*6001]:
            with self.assertRaises(ValueError):readable_text(raw)
    def test_math_preserves_operators(self):
        self.assertEqual(readable_text('2 + 2 = ?'),'2 + 2 = ?')
    def test_direct_answer_payload_and_validation(self):
        with patch('reading.complete_payload',return_value=json.dumps({'answer':'Улаанбаатар','reason':''})) as request:
            answer=answer_question('Монгол Улсын нийслэл?',object(),[],time.monotonic()+30)
            self.assertEqual(answer,'Хариулт: Улаанбаатар')
            self.assertIn('Монгол Улсын нийслэл?',request.call_args.args[1]['messages'][1]['content'])
        with patch('reading.complete_payload',return_value='{"answer": "", "reason": ""}'):
            with self.assertRaises(ValueError):answer_question('Монгол Улсын нийслэл?',object(),[],time.monotonic()+30)
    def test_complete_quiz_still_uses_validated_choice(self):
        with patch('reading.suggest_quiz',return_value='Хариулт: B') as quiz:
            answer_question('Монгол Улсын нийслэл?\nA. Дархан\nB. Улаанбаатар\nC. Эрдэнэт\nD. Ховд',object(),[],time.monotonic()+30)
            quiz.assert_called_once()

    def test_cache_keeps_math_symbols_and_decimal_points(self):
        from core import Deduper
        d=Deduper();d.check('2 + 2 = ?',True)
        self.assertFalse(d.check('2 - 2 = ?')[0])
        d.check('1.5 + 2',True)
        self.assertFalse(d.check('15 + 2')[0])
