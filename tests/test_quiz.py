import json,time,unittest
from unittest.mock import MagicMock,patch
from quiz import parse_quiz,validate_suggestion,suggest_quiz
RAW='Монгол Улсын нийслэл аль вэ?\nA. Дархан\nB. Улаанбаатар\nC. Эрдэнэт\nD. Ховд'
class QuizTests(unittest.TestCase):
    def test_parse_multiline(self):
        q=parse_quiz(RAW.replace('Улаанбаатар','Улаан\nбаатар'));self.assertEqual(q.options['B'],'Улаан баатар');self.assertIn('нийслэл',q.question)
    def test_timer_and_cyrillic(self):
        q=parse_quiz(RAW.replace('A.','А.').replace('B.','В.').replace('C.','С.').replace('D.','Д.')+'\n00:29\nSubmit');self.assertEqual(q.options['D'],'Ховд')
    def test_missing_option(self):
        with self.assertRaises(ValueError):parse_quiz(RAW.rsplit('\n',1)[0])
    def test_two_questions(self):
        with self.assertRaises(ValueError):parse_quiz(RAW+'\n'+RAW)
    def test_confidence_validation(self):
        with self.assertRaises(ValueError):validate_suggestion({'choice':'E','reason':'bad','confidence':'high'})
        with self.assertRaises(ValueError):validate_suggestion({'choice':'A','reason':'bad','confidence':0.9})
    def test_expired_no_network(self):
        with self.assertRaises(TimeoutError):suggest_quiz(parse_quiz(RAW),None,[],time.monotonic()-1)
    def test_structured_request(self):
        engine=MagicMock(endpoint='http://127.0.0.1:12345/v1/chat/completions',key='test')
        result={'choice':'B','reason':'Улаанбаатар нь нийслэл.','confidence':'high'}
        response=MagicMock();response.__enter__.return_value.read.return_value=json.dumps({'choices':[{'message':{'content':json.dumps(result)}}]}).encode()
        opener=MagicMock();opener.open.return_value=response
        with patch('quiz.build_opener',return_value=opener), patch('quiz.time.monotonic',return_value=100.0):
            answer=suggest_quiz(parse_quiz(RAW),engine,[],102.0)
            self.assertIn('Хариулт: B',answer);self.assertIn('моделийн өөрийн үнэлгээ',answer)
            payload=json.loads(opener.open.call_args.args[0].data);self.assertIn('response_format',payload)
            self.assertLessEqual(opener.open.call_args.kwargs['timeout'],2)
