import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("codexbar", ROOT / "src/codexbar.py")
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


class QuotaTests(unittest.TestCase):
    def test_missing_and_fractional_usage(self):
        for window in [None, {}, {"usedPercent": None}, {"usedPercent": True}, {"usedPercent": float("nan")}]:
            self.assertIsNone(c.remaining(window))
        self.assertEqual(c.remaining({"usedPercent": 22.8}), 77)
        self.assertEqual(c.remaining({"usedPercent": 120}), 0)
        self.assertEqual(c.remaining({"usedPercent": -1}), 100)

    def test_codex_bucket_only(self):
        snapshot = {"limitId": "codex", "primary": {"usedPercent": 22}}
        self.assertEqual(c.select_snapshot({"rateLimitsByLimitId": {"codex": snapshot}, "rateLimits": {}}), snapshot)
        self.assertEqual(c.select_snapshot({"rateLimits": snapshot}), snapshot)
        with self.assertRaises(c.UsageError):
            c.select_snapshot({"rateLimitsByLimitId": {"other": {}}, "rateLimits": snapshot})
        with self.assertRaises(c.UsageError):
            c.select_snapshot({"rateLimits": {"limitId": "other"}})

    def test_actual_windows_and_missing_secondary(self):
        rows = c.windows({"primary": {"usedPercent": 25, "windowDurationMins": 15}})
        self.assertEqual(rows[0][:2], ("15m", 75))
        self.assertEqual(rows[1][:2], ("7d", None))
        self.assertEqual(c.label({"windowDurationMins": 10080}, "?"), "7d")

    def test_fallback_no_fake_zero(self):
        with patch.object(c, "render_image", side_effect=OSError):
            text = c.menu({}, "Light")
        self.assertIn("--%", text)
        self.assertNotIn("0%", text)

    def test_explicit_invalid_codex_is_not_silently_ignored(self):
        with self.assertRaises(c.UsageError):
            c.find_codex("/does/not/exist")


class InstallTests(unittest.TestCase):
    def test_setup_upgrade_uninstall_and_spaces(self):
        with tempfile.TemporaryDirectory(prefix="codex bar '") as root:
            folder = Path(root)
            launcher = folder / "launcher $x"
            output = folder / "arguments"
            launcher.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > ' + c.shlex.quote(str(output)) + '\n')
            launcher.chmod(0o755)
            path = c.setup(folder, launcher, "/path with space/codex")
            subprocess.run([str(path)], check=True)
            self.assertEqual(output.read_text().splitlines(), ["menu", "--codex", "/path with space/codex"])
            c.setup(folder, launcher)
            self.assertTrue(c.uninstall(folder))
            self.assertFalse(c.uninstall(folder))

    def test_never_overwrite_foreign_plugin_or_symlink(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            path = folder / c.PLUGIN
            path.write_text("user content")
            with self.assertRaises(c.UsageError):
                c.setup(folder, "/bin/true")
            with self.assertRaises(c.UsageError):
                c.uninstall(folder)
            path.unlink()
            other = folder / "other"
            other.write_text(c.MARKER)
            path.symlink_to(other)
            with self.assertRaises(c.UsageError):
                c.setup(folder, "/bin/true")
            self.assertEqual(other.read_text(), c.MARKER)


class ProtocolTests(unittest.TestCase):
    def fake(self, directory, body):
        path = Path(directory) / "codex"
        # Invoke through an executable shell wrapper to tolerate Python paths with spaces.
        script = Path(directory) / "server.py"
        script.write_text("import sys,json,time,os\n" + body)
        path.write_text("#!/bin/sh\nexec " + c.shlex.join([sys.executable, str(script)]) + "\n")
        path.chmod(0o755)
        return str(path)

    def test_fragmented_and_batched_messages(self):
        with tempfile.TemporaryDirectory() as root:
            executable = self.fake(root, '''m=json.loads(input())
assert m['method']=='initialize'
sys.stdout.write('{"id":1,');sys.stdout.flush();time.sleep(.02)
sys.stdout.write('"result":{}}\\n');sys.stdout.flush()
assert json.loads(input())['method']=='initialized'
assert json.loads(input())['method']=='account/rateLimits/read'
print(json.dumps({'method':'notice'}))
print(json.dumps({'id':2,'result':{'rateLimitsByLimitId':{'codex':{'primary':{'usedPercent':22}}}}}),flush=True)
time.sleep(10)
''')
            self.assertEqual(c.read_limits(executable, timeout=2)["primary"]["usedPercent"], 22)

    def test_eof_and_partial_line_timeout(self):
        with tempfile.TemporaryDirectory() as root:
            executable = self.fake(root, "input()\n")
            with self.assertRaises(c.UsageError):
                c.read_limits(executable, timeout=1)
            executable = self.fake(root, "input();print('{',end='',flush=True);time.sleep(10)\n")
            start = time.monotonic()
            with self.assertRaises(c.UsageError):
                c.read_limits(executable, timeout=.15)
            self.assertLess(time.monotonic() - start, 3)

    def test_server_error_does_not_leak_response(self):
        with tempfile.TemporaryDirectory() as root:
            executable = self.fake(root, '''input()
print(json.dumps({'id':1,'error':{'message':'SECRET'}}),flush=True)
time.sleep(10)
''')
            with self.assertRaises(c.UsageError) as error:
                c.read_limits(executable)
            self.assertNotIn("SECRET", str(error.exception))


class RendererTests(unittest.TestCase):
    @unittest.skipUnless((ROOT / ".build/install/libexec/usage-renderer").exists(), "Run make check to build the renderer")
    def test_png_and_invalid_input(self):
        import base64
        import struct
        renderer = ROOT / ".build/install/libexec/usage-renderer"
        for appearance in ("Light", "Dark"):
            for values in ((52, 42), (100, 0), (None, None)):
                data = json.dumps([{"label": "5h", "percent": values[0]}, {"label": "7d", "percent": values[1]}])
                result = subprocess.run([str(renderer), appearance], input=data, text=True, capture_output=True, check=True)
                png = base64.b64decode(result.stdout.strip(), validate=True)
                self.assertEqual(struct.unpack(">II", png[16:24]), (240, 66))
        result = subprocess.run([str(renderer), "Light"], input="[]", text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
