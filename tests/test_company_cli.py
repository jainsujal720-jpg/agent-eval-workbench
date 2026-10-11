import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.session_eval import _summary_report, main


class CompanyCliTests(unittest.TestCase):
    def test_summary_report_drops_prompts_answers_ids_and_free_text(self):
        report = {
            'provider': 'company-api', 'passed': False,
            'metrics': {'turn_count': 1, 'success_by_category': {'internal-project-codename': 0.0}},
            'cases': [{
                'id': 'private-customer-identifier', 'input': 'private customer message',
                'answer': 'private model response', 'success': False,
                'category': 'authorization', 'tool_correct': False,
                'access_correct': True, 'tool_outcome_correct': True,
                'policy_violations': ['private policy phrase'],
                'missing_expected': ['private expected sentence'], 'error': None,
            }],
        }
        safe = json.dumps(_summary_report(report))
        for private_value in ('private-customer-identifier', 'private customer message',
                              'private model response', 'private policy phrase',
                              'private expected sentence', 'internal-project-codename'):
            self.assertNotIn(private_value, safe)
        self.assertFalse(_summary_report(report)['cases'][0]['success'])

    def test_company_api_cli_writes_summary_and_keeps_stdout_free_of_case_content(self):
        fake_report = {
            'provider': 'company-api', 'passed': False,
            'metrics': {'turn_count': 1, 'failed_turn_count': 1},
            'cases': [{
                'id': 'secret-customer-id', 'input': 'private prompt text',
                'answer': 'private answer text', 'success': False,
                'category': 'authorization', 'tool_correct': False,
                'access_correct': True, 'tool_outcome_correct': True,
                'policy_violations': [], 'missing_expected': [], 'error': None,
            }],
        }
        with tempfile.TemporaryDirectory() as directory:
            benchmark = Path(directory) / 'benchmark.jsonl'
            output = Path(directory) / 'summary.json'
            benchmark.write_text('{"synthetic": true}\n')
            captured = io.StringIO()
            with patch('sys.argv', ['session_eval', '--target', 'company-api',
                                    '--benchmark', str(benchmark), '--output', str(output)]), \
                    patch.dict(os.environ, {'AGENTEVAL_AUTH_TOKEN': 'test-secret'}), \
                    patch('app.session_eval.evaluate_sessions', return_value=fake_report), \
                    patch('app.api_adapter.staging_target', return_value={'provider': 'test-api'}), \
                    contextlib.redirect_stdout(captured):
                result = main()
            self.assertEqual(result, 1)
            for private_value in ('secret-customer-id', 'private prompt text', 'private answer text'):
                self.assertNotIn(private_value, captured.getvalue())
                self.assertNotIn(private_value, output.read_text())
            saved = json.loads(output.read_text())
            self.assertFalse(saved['content_included'])
            self.assertEqual(saved['cases'][0]['case_number'], 1)


if __name__ == '__main__':
    unittest.main()
