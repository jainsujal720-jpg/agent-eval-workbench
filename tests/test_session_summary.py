import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from app import session_eval


class SessionSummaryTests(TestCase):
    def test_summary_only_output_has_numbered_checks_without_conversation_content(self):
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'summary.json'
            argv=['session_eval','--benchmark','benchmarks/support_sessions.jsonl',
                  '--output',str(output),'--summary-only']
            stdout=io.StringIO()
            with patch.object(sys,'argv',argv),contextlib.redirect_stdout(stdout):
                exit_code=session_eval.main()
            saved=json.loads(output.read_text())
            printed=json.loads(stdout.getvalue())
        self.assertEqual(exit_code,0)
        self.assertTrue(saved['passed'])
        self.assertEqual(saved['metrics']['session_count'],8)
        self.assertEqual(len(saved['cases']),18)
        self.assertEqual(saved['cases'][0]['case_number'],1)
        self.assertNotIn('input',json.dumps(saved))
        self.assertNotIn('answer',json.dumps(saved))
        self.assertNotIn('customer_id',json.dumps(saved))
        self.assertEqual(printed,saved)
