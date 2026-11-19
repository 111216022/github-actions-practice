import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from cryptography.exceptions import InvalidTag
from scripts.crypto_testcases import decrypt, encrypt, generate_keys


ROOT = Path(__file__).resolve().parents[1]


class CryptoTestcasesTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="encrypted testcase ")
        self.addCleanup(directory.cleanup)
        self.folder = Path(directory.name)
        self.private = self.folder / "private.pem"
        self.public = self.folder / "public.pem"
        generate_keys(self.private, self.public)
        self.data = json.dumps([
            {"id": "空白", "input": "  2\t3\r\n", "expected": "5\n"},
            {"id": "zero", "input": "0 0\n", "expected": "0\n"},
        ], ensure_ascii=False).encode("utf-8")
        self.encrypted = self.folder / "測資.json.enc"
        self.encrypted.write_bytes(encrypt(self.data, self.public.read_bytes()))

    def test_roundtrip_preserves_bytes_and_randomizes_ciphertext(self):
        self.assertEqual(decrypt(self.encrypted.read_bytes(), self.private.read_bytes()), self.data)
        self.assertNotEqual(encrypt(self.data, self.public.read_bytes()), self.encrypted.read_bytes())

    def test_tampered_ciphertext_and_wrong_key_are_rejected(self):
        data = bytearray(self.encrypted.read_bytes())
        data[-1] ^= 1
        with self.assertRaises(InvalidTag):
            decrypt(bytes(data), self.private.read_bytes())
        other = self.folder / "other.pem"
        generate_keys(other, self.folder / "other-public.pem")
        with self.assertRaises(InvalidTag):
            decrypt(self.encrypted.read_bytes(), other.read_bytes())

    def test_bad_format_and_schema_are_rejected(self):
        for data in (b"", b"not encrypted", self.encrypted.read_bytes()[:30]):
            with self.subTest(data=data[:10]), self.assertRaises(ValueError):
                decrypt(data, self.private.read_bytes())
        for data in (b"[]", b"{}", b"not json", b'[{"id":"x","input":1,"expected":""}]'):
            with self.subTest(data=data), self.assertRaises(ValueError):
                encrypt(data, self.public.read_bytes())

    def test_keygen_does_not_overwrite_keys(self):
        original = self.private.read_bytes()
        with self.assertRaises(ValueError):
            generate_keys(self.private, self.public)
        self.assertEqual(self.private.read_bytes(), original)

    def run_validator(self, script="import sys; print(sum(map(int, sys.stdin.read().split())))", *extra, embedded=False):
        cli = "validator.exe" if os.name == "nt" else "validator"
        shutil.copy2(ROOT / cli, self.folder / cli)
        (self.folder / "scripts").mkdir(exist_ok=True)
        shutil.copy2(ROOT / "scripts/crypto_testcases.py", self.folder / "scripts/crypto_testcases.py")
        (self.folder / "hello.py").write_text(script, encoding="utf-8")
        key_args = [] if embedded else ["--private-key", str(self.private)]
        return subprocess.run([
            str(self.folder / cli), "--python", sys.executable,
            "--testcases", str(self.encrypted), *key_args, *extra,
        ], cwd=self.folder, capture_output=True, encoding="utf-8", timeout=20)

    def test_embedded_key_works_without_private_key_file(self):
        self.encrypted.write_bytes(encrypt(self.data, (ROOT / "keys/public_key.pem").read_bytes()))
        self.private.unlink()
        result = self.run_validator(embedded=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.count("PASS"), 2)

    def test_embedded_key_rejects_other_recipient(self):
        result = self.run_validator("print('MUST NOT EXECUTE')", embedded=True)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("MUST NOT EXECUTE", result.stdout)

    def test_explicit_missing_key_does_not_fall_back_to_embedded_key(self):
        self.encrypted.write_bytes(encrypt(self.data, (ROOT / "keys/public_key.pem").read_bytes()))
        self.private.unlink()
        result = self.run_validator()
        self.assertEqual(result.returncode, 2)

    def test_validator_runs_all_cases_without_plaintext_file(self):
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.count("PASS"), 2)
        self.assertFalse((self.folder / "測資.json").exists())

    def test_validator_continues_after_wrong_answer(self):
        result = self.run_validator("print(0)")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout.count("FAIL"), 1)
        self.assertEqual(result.stdout.count("PASS"), 1)

    def test_validator_rejects_tampering_before_running_hello(self):
        data = bytearray(self.encrypted.read_bytes())
        data[-1] ^= 1
        self.encrypted.write_bytes(data)
        result = self.run_validator("print('MUST NOT EXECUTE')")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("MUST NOT EXECUTE", result.stdout)
        self.assertIn("Decryption failed", result.stderr)

    def test_timeout_applies_to_each_case(self):
        result = self.run_validator("import time; time.sleep(5)", "--timeout", "0.1")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout.count("FAIL"), 2)


if __name__ == "__main__":
    unittest.main()
