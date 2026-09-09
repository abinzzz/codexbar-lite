import importlib.util
import io
import selectors
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
PREFIX = Path(os.environ.get("CODEXBAR_TEST_PREFIX", ROOT / ".build/install"))
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
            self.assertEqual(output.read_text().splitlines(), ["stream", "--codex", "/path with space/codex"])
            self.assertIn("<swiftbar.type>streamable</swiftbar.type>", path.read_text())
            self.assertIn("<swiftbar.useTrailingStreamSeparator>true", path.read_text())
            c.setup(folder, launcher, no_animation=True)
            subprocess.run([str(path)], check=True)
            self.assertEqual(output.read_text().splitlines(), ["stream", "--no-animation"])
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
    @unittest.skipUnless((PREFIX / "libexec/usage-renderer").exists(), "Run make check to build the renderer")
    def test_png_and_invalid_input(self):
        import base64
        import struct
        renderer = PREFIX / "libexec/usage-renderer"
        for appearance in ("Light", "Dark"):
            for values in ((52, 42), (100, 0), (None, None)):
                data = json.dumps([{"label": "5h", "percent": values[0]}, {"label": "7d", "percent": values[1]}])
                result = subprocess.run([str(renderer), appearance], input=data, text=True, capture_output=True, check=True)
                png = base64.b64decode(result.stdout.strip(), validate=True)
                self.assertEqual(struct.unpack(">II", png[16:24]), (240, 66))
        result = subprocess.run([str(renderer), "Light"], input="[]", text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)


class StartupTests(unittest.TestCase):
    snapshot = {"primary": {"usedPercent": 0}, "secondary": {"usedPercent": 15}}

    def test_ramp_monotonic_endpoints_and_unknown(self):
        frames = c.startup_rows(self.snapshot)
        self.assertEqual([r[1] for r in frames[0]], [0, 0])
        self.assertEqual([r[1] for r in frames[-1]], [100, 85])
        for index in (0, 1):
            values = [frame[index][1] for frame in frames]
            self.assertEqual(values, sorted(values))
        frames = c.startup_rows({"primary": {"usedPercent": 50}})
        self.assertTrue(all(frame[1][1] is None for frame in frames))
        self.assertEqual(frames[-1][0][1], 50)

    def test_one_second_after_prerender_with_authoritative_dropdown(self):
        now = [0.0]
        records = []
        def render(frames, appearance):
            now[0] += 2  # Slow preparation must not change playback duration.
            return ["image" for _ in frames]
        def sleep(delay):
            now[0] += delay
        with patch.object(c, "render_frames", side_effect=render):
            c.animate_startup(self.snapshot, "Dark", lambda doc: records.append((now[0], doc)),
                              clock=lambda: now[0], sleep=sleep)
        self.assertEqual(len(records), 31)
        self.assertAlmostEqual(records[-1][0] - records[0][0], 1.0)
        self.assertIn("5h 0%", records[0][1])
        self.assertIn("5h 100%", records[-1][1])
        self.assertIn("7d 85%", records[-1][1])
        self.assertIn("5h remaining: 100%", records[0][1])
        self.assertIn("stdin=refresh", records[-1][1])
        self.assertNotIn("refresh=true", records[-1][1])

    def test_first_success_only_even_after_error_unknown_and_refresh(self):
        from unittest.mock import Mock
        fetch = Mock(side_effect=[c.UsageError("Not ready"), {}, self.snapshot, self.snapshot])
        wait = Mock(side_effect=[True, True, True, False])
        output = []
        with patch.object(c, "animate_startup") as animation, patch.object(c, "render_image", side_effect=OSError):
            c.run_stream(fetch, "Light", output.append, wait)
        animation.assert_called_once()
        self.assertIn("stdin=refresh", output[1])
        self.assertIn("--%", output[2])
        self.assertEqual(fetch.call_count, 4)
        self.assertTrue(all(0 <= call.args[0] <= 60 for call in wait.call_args_list))

    def test_disable_animation_and_zero_quota(self):
        for snapshot, animate in [(self.snapshot, False), ({"primary": {"usedPercent": 100}}, True)]:
            with patch.object(c, "animate_startup") as animation, patch.object(c, "render_image", side_effect=OSError):
                c.run_stream(lambda: snapshot, "Light", lambda _: None, lambda _: False, animate=animate)
            animation.assert_not_called()

    def test_renderer_failure_falls_back_to_final_value(self):
        output = []
        with patch.object(c, "render_frames", side_effect=OSError), patch.object(c, "render_image", side_effect=OSError):
            c.animate_startup(self.snapshot, "Light", output.append)
        self.assertEqual(len(output), 1)
        self.assertIn("5h 100%", output[0])

    def test_complete_frame_separator(self):
        output = io.StringIO()
        with patch.object(sys, "stdout", output):
            c.emit_frame("header\n---\nmenu")
        self.assertEqual(output.getvalue(), "header\n---\nmenu\n~~~\n")

    def test_refresh_input_fragment_timer_and_eof(self):
        reader_fd, writer_fd = os.pipe()
        with os.fdopen(reader_fd, "rb", buffering=0) as reader:
            control = c.RefreshInput(reader)
            try:
                os.write(writer_fd, b"ref")
                self.assertTrue(control.wait(.01))  # Timer can fire on partial input.
                os.write(writer_fd, b"resh\n")
                self.assertTrue(control.wait(1))
                os.close(writer_fd)
                self.assertFalse(control.wait(1))
            finally:
                control.close()

    @unittest.skipUnless((PREFIX / "libexec/usage-renderer").exists(), "Build renderer first")
    def test_batch_frames_match_single_frame_renderer(self):
        with patch.object(c, "renderer_path", return_value=PREFIX / "libexec/usage-renderer"):
            for appearance in ("Light", "Dark"):
                rows = c.startup_rows(self.snapshot)
                images = c.render_frames(rows, appearance)
                self.assertEqual(images[0], c.render_image(rows[0], appearance))
                self.assertEqual(images[-1], c.render_image(rows[-1], appearance))
                self.assertNotEqual(images[0], images[-1])

    @unittest.skipUnless((PREFIX / "bin/codexbar-lite").exists(), "Build CLI first")
    def test_stream_process_manual_refresh_and_shutdown(self):
        with subprocess.Popen([str(PREFIX / "bin/codexbar-lite"), "stream", "--demo", "--no-animation"],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
            selector = selectors.DefaultSelector()
            selector.register(proc.stdout, selectors.EVENT_READ)
            pending = bytearray()
            def receive():
                deadline = time.monotonic() + 10
                while b"\n~~~\n" not in pending:
                    self.assertGreater(deadline, time.monotonic(), "Stream frame timeout")
                    if selector.select(.1):
                        data = os.read(proc.stdout.fileno(), 65536)
                        self.assertTrue(data, "Unexpected EOF")
                        pending.extend(data)
                frame, _, rest = pending.partition(b"\n~~~\n")
                pending[:] = rest
                return frame.decode()
            try:
                self.assertIn("Loading", receive())
                first = receive()
                self.assertIn("5h 52%", first)
                self.assertIn("image=", first)
                proc.stdin.write(b"refresh\n")
                proc.stdin.flush()
                self.assertEqual(receive(), first)  # Refresh emits one final frame, without loading/ramp.
                proc.stdin.close()
                self.assertEqual(proc.wait(timeout=3), 0)
            finally:
                selector.close()
                if proc.poll() is None:
                    proc.terminate()
                    proc.wait(timeout=3)


if __name__ == '__main__':
    unittest.main()
