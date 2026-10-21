"""요약 언어 = 맥 시스템 언어. 언어가 바뀌면 이어 쓰지 않고 새 언어로 처음부터 다시 정리한다. 외부 모델은 부르지 않는다."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import board as B

ANSWER = '{"title":"Fix login","summary":"s","last_reply":"r","steps":[{"label":"Check","state":"done","detail":"d"}],"items":[]}'


class SummaryLangTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='spyhop-lang-')
        self.saved = (B.AUTO, dict(B._SYSLANG))
        B.AUTO = self.tmp.name
        self.log = Path(self.tmp.name) / 's.jsonl'
        self.log.write_text(json.dumps({'type': 'user', 'message': {'role': 'user', 'content': 'hello'}}) + '\n')

    def tearDown(self):
        B.AUTO, sl = self.saved
        B._SYSLANG.clear()
        B._SYSLANG.update(sl)
        self.tmp.cleanup()

    def run_in(self, code):
        B._SYSLANG.update(code=code, at=9e18)
        with patch.object(B, 'llm', return_value=ANSWER) as model, patch.object(B, 'current_summarizer', return_value='test'):
            res = B.summarize(str(self.log))
        return res, model

    def test_prompt_uses_system_language_and_records_it(self):
        res, model = self.run_in('en')
        self.assertIn('English', model.call_args.args[0])
        self.assertNotIn('__LANG__', model.call_args.args[0])
        self.assertEqual(res['lang'], 'en')

    def test_language_change_resummarizes_from_scratch(self):
        self.run_in('ko')
        res, model = self.run_in('en')  # 크기도 그대로고 1분도 안 지났지만 언어가 바뀌었으니 다시 부른다
        model.assert_called_once()
        self.assertNotIn('<이전 정리>', model.call_args.args[1])
        self.assertEqual(res['lang'], 'en')

    def test_same_language_uses_cache(self):
        self.run_in('ko')
        _, model = self.run_in('ko')
        model.assert_not_called()


if __name__ == '__main__':
    unittest.main()
