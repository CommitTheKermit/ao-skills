import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("preflight", Path(__file__).with_name("preflight-install.py"))
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


class PreflightTest(unittest.TestCase):
    def meta(self, code=3, signer="abc", package="app.test"):
        return dict(package=package, version_code=code, version_name="1.0", signer_sha256=[signer])

    def test_update_and_new_install(self):
        self.assertTrue(preflight.compare(self.meta(4), self.meta(3), "app.test")["allowed"])
        self.assertEqual(preflight.compare(self.meta(), None, "app.test")["installation"], "new")

    def test_downgrade_and_signer_mismatch_blocked(self):
        self.assertIn("version_downgrade", preflight.compare(self.meta(2), self.meta(), "app.test")["reasons"])
        self.assertFalse(preflight.compare(self.meta(signer="new"), self.meta(), "app.test")["allowed"])

    def test_wrong_target_package(self):
        self.assertFalse(preflight.compare(self.meta(package="wrong.app"), None, "app.test")["allowed"])

    def test_version_name_not_numeric_order(self):
        old = dict(self.meta(), version_name="9.9")
        self.assertTrue(preflight.compare(self.meta(4), old, "app.test")["allowed"])

    def test_installed_query_uses_explicit_serial_and_no_mutation(self):
        with patch.object(preflight, "run", return_value="") as command:
            self.assertIsNone(preflight.installed_metadata("adb", "physical-1", "app.test", "aapt", "apksigner"))
        self.assertEqual(command.call_args.args[0][:3], ["adb", "-s", "physical-1"])
        self.assertIn("list", command.call_args.args[0])

    def test_query_failure_not_treated_as_absent(self):
        with patch.object(preflight, "run", side_effect=ValueError("offline")):
            with self.assertRaises(ValueError):
                preflight.installed_metadata("adb", "device-1", "app.test", "aapt", "apksigner")

    def test_apk_parse_and_missing_signer(self):
        output = "package: name='app.test' versionCode='4' versionName='1.2' platformBuildVersionName='15'"
        with patch.object(preflight, "run", side_effect=[output,"Signer #1 certificate SHA-256 digest: AABB"]):
            self.assertEqual(preflight.apk_metadata("aapt","signer","target.apk")["signer_sha256"], ["aabb"])
        with patch.object(preflight, "run", side_effect=[output,""]):
            with self.assertRaises(ValueError):
                preflight.apk_metadata("aapt","signer","target.apk")

    def test_lease_owned_serial_only(self):
        import json
        with tempfile.TemporaryDirectory() as directory:
            Path(directory,"lease.json").write_text(json.dumps(dict(owner="mine",serial="emulator-5554")))
            with patch.dict(os.environ, CODEX_ANDROID_LEASE_DIR=directory, CODEX_THREAD_ID="mine"):
                preflight.require_lease("emulator-5554")
                with self.assertRaises(ValueError):
                    preflight.require_lease("emulator-5556")


if __name__ == "__main__":
    unittest.main()
