import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app import benchmark_upload
from app.upload_security import reject_credential_like_content


class UploadSecurityTests(unittest.TestCase):
    def test_rejects_populated_credential_fields_without_echoing_value(self):
        content = json.dumps([{"id": "case-1", "input": "hello", "api_key": "not-a-real-key-123"}])
        with self.assertRaisesRegex(ValueError, "credential field") as raised:
            reject_credential_like_content(content)
        self.assertNotIn("not-a-real-key-123", str(raised.exception))

    def test_rejects_common_secret_shapes_in_text(self):
        with self.assertRaisesRegex(ValueError, "credential or secret"):
            reject_credential_like_content("my AWS key is AKIA1234567890ABCDEF")

    def test_allows_redacted_credentials_and_security_test_prompts(self):
        content = json.dumps([{
            "id": "security-case",
            "input": "Do not share your password or verification code.",
            "api_key": "REDACTED",
        }])
        reject_credential_like_content(content)

    def test_upload_rejects_secret_before_writing_file(self):
        content = json.dumps([{
            "id": "case-1",
            "customer_id": "alice",
            "category": "status",
            "password": "correct-horse-battery",
            "turns": [{
                "input": "hello",
                "expected_tool": "ask_order_id",
                "expected_contains": [],
                "expected_accessed_order_ids": [],
            }],
        }])
        with tempfile.TemporaryDirectory() as folder, patch.object(benchmark_upload, "UPLOADS", Path(folder)):
            with self.assertRaisesRegex(ValueError, "credential field"):
                benchmark_upload.upload(content)
            self.assertEqual(list(Path(folder).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
