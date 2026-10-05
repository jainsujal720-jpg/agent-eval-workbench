import json
import os
import sys
import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch
from app.agent import run_openai_agent


class LiveFormatterTests(unittest.TestCase):
    def run_call(self, text, name, args):
        call = NS(function=NS(name=name, arguments=json.dumps(args)))
        response = NS(choices=[NS(message=NS(tool_calls=[call]))], usage=None)
        sdk = NS(OpenAI=lambda **kw: NS(chat=NS(completions=NS(create=lambda **kw: response))))
        with patch.dict(sys.modules, {'openai': sdk}), patch.dict(os.environ, {'OPENAI_API_KEY': 'test-placeholder'}):
            return run_openai_agent(text)

    def test_refund_typo_uses_classified_intent(self):
        result = self.run_call('refnd A-1002', 'lookup_order', {'order_id':'A-1002', 'intent':'refund'})
        self.assertIn('not currently eligible', result.answer)
        self.assertIn('not submitted or approved', result.answer)

    def test_delivered_status_does_not_add_refund(self):
        result = self.run_call('Where is A-1001?', 'lookup_order', {'order_id':'A-1001', 'intent':'status'})
        self.assertEqual(result.answer, 'Order A-1001 is delivered.')

    def test_multiple_order_clarification(self):
        result = self.run_call('A-1001 and A-1002', 'ask_order_id', {'reason':'multiple_orders'})
        self.assertIn('which order', result.answer.lower())
        self.assertEqual(result.tool, 'ask_order_id')

    def test_wrong_model_route_remains_visible(self):
        result = self.run_call('A-1001 and A-1002', 'lookup_order', {'order_id':'A-1001', 'intent':'status'})
        self.assertEqual(result.tool, 'order_lookup')

    def test_invalid_intent_is_not_silently_accepted(self):
        with self.assertRaises(ValueError):
            self.run_call('A-1001', 'lookup_order', {'order_id':'A-1001', 'intent':'invented'})
