"""Codexbar Lite: a read-only Codex quota client and SwiftBar integration."""
import argparse
import base64
import datetime as dt
import json
import math
import os
from pathlib import Path
import selectors
import signal
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

VERSION = "0.2.0"
PLUGIN = "codexbar-lite.1m.sh"
MARKER = "# Managed by codexbar-lite"
ROOT = Path(__file__).resolve().parent
REFRESH_SECONDS = 60
ANIMATION_SECONDS = 1.0
ANIMATION_STEPS = 30


class UsageError(Exception):
    pass


def find_codex(explicit=None):
    override = explicit or os.environ.get("CODEXBAR_CODEX")
    candidates = [override] if override else [shutil.which("codex"), "/opt/homebrew/bin/codex", "/usr/local/bin/codex"]
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return str(Path(candidate).absolute())
    raise UsageError("Codex CLI not found. Install Codex, or use --codex /absolute/path/to/codex.")


def read_limits(executable, timeout=15):
    """Use byte-oriented reads so partial/multiple JSON lines cannot bypass the deadline."""
    with subprocess.Popen([executable, "app-server", "--stdio"], stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as process:
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        deadline = time.monotonic() + timeout
        pending = bytearray()
        initialized = False

        def send(value):
            process.stdin.write(json.dumps(value).encode() + b"\n")
            process.stdin.flush()

        try:
            send({"id": 1, "method": "initialize", "params": {
                "clientInfo": {"name": "codexbar-lite", "version": VERSION},
                "capabilities": {"experimentalApi": True}}})
            while time.monotonic() < deadline:
                if not selector.select(max(0, min(0.2, deadline - time.monotonic()))):
                    continue
                chunk = os.read(process.stdout.fileno(), 65536)
                if not chunk:
                    raise UsageError("Codex app-server exited before returning usage.")
                pending.extend(chunk)
                if len(pending) > 2 * 1024 * 1024:
                    raise UsageError("Codex app-server response is too large.")
                while b"\n" in pending:
                    line, _, pending = pending.partition(b"\n")
                    if not line.strip():
                        continue
                    message = json.loads(line)
                    if not isinstance(message, dict):
                        raise UsageError("Unexpected Codex response.")
                    if message.get("id") == 1 and not initialized:
                        if "error" in message:
                            raise UsageError("Codex initialization failed. Update the Codex CLI.")
                        send({"method": "initialized"})
                        send({"id": 2, "method": "account/rateLimits/read", "params": None})
                        initialized = True
                    elif message.get("id") == 2 and initialized:
                        if "error" in message:
                            raise UsageError("Usage unavailable. Run codex login with your ChatGPT account.")
                        return select_snapshot(message.get("result") or {})
                    elif "id" in message and "method" in message:
                        send({"id": message["id"], "error": {"code": -32601, "message": "Unsupported method"}})
            raise UsageError("Codex usage request timed out.")
        finally:
            selector.close()
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def select_snapshot(result):
    if not isinstance(result, dict):
        raise UsageError("Unexpected Codex quota response.")
    buckets = result.get("rateLimitsByLimitId")
    if buckets is not None and not isinstance(buckets, dict):
        raise UsageError("Unexpected Codex quota buckets.")
    if buckets:
        snapshot = buckets.get("codex")
        if not snapshot:
            raise UsageError("No Codex quota bucket is available for this account.")
    else:
        snapshot = result.get("rateLimits")
    if not isinstance(snapshot, dict) or snapshot.get("limitId") not in (None, "codex"):
        raise UsageError("No Codex quota bucket is available for this account.")
    return snapshot


def remaining(window):
    value = window.get("usedPercent") if isinstance(window, dict) else None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return round(max(0, min(100, 100 - value)))


def label(window, fallback):
    duration = window.get("windowDurationMins") if isinstance(window, dict) else None
    if isinstance(duration, bool) or not isinstance(duration, int) or duration <= 0:
        return fallback
    if duration % 1440 == 0:
        return f"{duration // 1440}d"
    if duration % 60 == 0:
        return f"{duration // 60}h"
    return f"{duration}m"


def windows(snapshot):
    return [(label(snapshot.get(key), default), remaining(snapshot.get(key)), snapshot.get(key))
            for key, default in (("primary", "5h"), ("secondary", "7d"))]


def reset_text(window):
    timestamp = window.get("resetsAt") if isinstance(window, dict) else None
    if not isinstance(timestamp, (int, float)) or isinstance(timestamp, bool):
        return "Unknown"
    try:
        return dt.datetime.fromtimestamp(timestamp).astimezone().strftime("%m-%d %H:%M %Z")
    except (ValueError, OverflowError, OSError):
        return "Unknown"


def renderer_path():
    return ROOT / "usage-renderer"


def render_image(rows, appearance):
    payload = [{"label": title, "percent": percent} for title, percent, _ in rows]
    result = subprocess.run([str(renderer_path()), appearance], input=json.dumps(payload),
                            text=True, capture_output=True, timeout=5, check=True)
    image = result.stdout.strip()
    if not base64.b64decode(image, validate=True).startswith(b"\x89PNG"):
        raise UsageError("Invalid renderer output.")
    return image


def menu(snapshot, appearance, *, image=None, frame_rows=None, stream=False):
    rows = windows(snapshot)
    display_rows = rows if frame_rows is None else frame_rows
    summary = " · ".join(f"{title} {percent if percent is not None else '--'}%" for title, percent, _ in display_rows)
    try:
        if image is None:
            image = render_image(display_rows, appearance)
        header = f"| image={image} width=80 height=22 dropdown=false tooltip='Codex remaining: {summary}'"
    except (OSError, ValueError, subprocess.SubprocessError, UsageError):
        header = f"{summary} | size=11 dropdown=false"
    output = [header, "---", "Codex | size=13"]
    for title, percent, window in rows:
        output.extend([f"{title} remaining: {percent if percent is not None else '--'}% | size=13",
                       f"--Resets: {reset_text(window)} | size=11"])
    output.extend(["---", "Refresh | " + ("stdin=refresh" if stream else "refresh=true"),
                   "Usage is shared across your Codex account. | size=11"])
    return "\n".join(output)


def startup_rows(snapshot):
    """Keep missing windows unknown and interpolate both known values together."""
    targets = windows(snapshot)
    return [[(title, None if value is None else round(value * step / ANIMATION_STEPS), window)
             for title, value, window in targets] for step in range(ANIMATION_STEPS + 1)]


def render_frames(frames, appearance):
    payload = [[{"label": title, "percent": value} for title, value, _ in rows] for rows in frames]
    result = subprocess.run([str(renderer_path()), appearance, "--batch"], input=json.dumps(payload),
                            text=True, capture_output=True, timeout=5, check=True)
    images = result.stdout.splitlines()
    if len(images) != len(frames) or any(not base64.b64decode(image, validate=True).startswith(b"\x89PNG")
                                       for image in images):
        raise UsageError("Invalid animation frames.")
    return images


def reduce_motion():
    try:
        result = subprocess.run([str(renderer_path()), "--preferences"], text=True,
                                capture_output=True, timeout=5, check=True)
        return result.stdout.strip() == "reduce-motion"
    except (OSError, subprocess.SubprocessError):
        return False


def emit_frame(document):
    # SwiftBar's trailing separator commits complete frames, including large PNGs.
    sys.stdout.write(document + "\n~~~\n")
    sys.stdout.flush()


def animate_startup(snapshot, appearance, emit, *, clock=time.monotonic, sleep=time.sleep):
    frames = startup_rows(snapshot)
    try:
        images = render_frames(frames, appearance)
        documents = [menu(snapshot, appearance, image=image, frame_rows=rows, stream=True)
                     for rows, image in zip(frames, images)]
    except (OSError, ValueError, UsageError, subprocess.SubprocessError):
        emit(menu(snapshot, appearance, stream=True))
        return
    # Render everything first so encoding and process startup cannot stretch the animation.
    started = clock()
    for step, document in enumerate(documents):
        deadline = started + ANIMATION_SECONDS * step / ANIMATION_STEPS
        delay = deadline - clock()
        if delay > 0:
            sleep(delay)
        emit(document)


class RefreshInput:
    """Wait without polling; SwiftBar writes newline-terminated stdin actions."""
    def __init__(self, source):
        self.selector = selectors.DefaultSelector()
        self.source = source
        self.pending = bytearray()
        self.closed = False
        try:
            self.selector.register(source, selectors.EVENT_READ)
        except PermissionError:
            # /dev/null and regular redirected files may not be selectable on macOS.
            self.closed = True

    def close(self):
        self.selector.close()

    def wait(self, timeout):
        if self.closed:
            return False
        deadline = time.monotonic() + timeout
        while True:
            if b"\n" in self.pending:
                lines = self.pending.split(b"\n")
                self.pending = bytearray(lines.pop())
                if any(line.strip() == b"refresh" for line in lines):
                    return True
            remaining_time = deadline - time.monotonic()
            if remaining_time <= 0:
                return True
            if not self.selector.select(remaining_time):
                return True
            data = os.read(self.source.fileno(), 4096)
            if not data:
                return False
            self.pending.extend(data)
            if len(self.pending) > 8192:
                self.pending.clear()


def error_menu(error, *, stream=False):
    message = str(error) if isinstance(error, UsageError) else "Local operation failed. Run codexbar-lite doctor."
    return ("Codex -- | size=11\n---\nUsage unavailable | size=13\n" + message +
            " | size=11\n---\nRetry | " + ("stdin=refresh" if stream else "refresh=true"))


def run_stream(fetch, appearance, emit, wait, *, animate=True, clock=time.monotonic):
    emit("Codex -- | size=11\n---\nLoading Codex quota… | size=13")
    startup_pending = True
    while True:
        started = clock()
        try:
            snapshot = fetch()
            values = [value for _, value, _ in windows(snapshot)]
            known = any(value is not None for value in values)
            if startup_pending and known:
                if animate and any(value is not None and value > 0 for value in values):
                    animate_startup(snapshot, appearance, emit)
                else:
                    emit(menu(snapshot, appearance, stream=True))
                startup_pending = False
            else:
                emit(menu(snapshot, appearance, stream=True))
        except (UsageError, OSError, ValueError, subprocess.SubprocessError) as error:
            emit(error_menu(error, stream=True))
        if not wait(max(0, REFRESH_SECONDS - (clock() - started))):
            break


def stop_stream(signum, frame):
    # Raising lets active quota subprocesses run their cleanup before exiting.
    raise SystemExit(0)


def plugin_directory(explicit=None):
    if explicit:
        return Path(explicit).expanduser().absolute()
    result = subprocess.run(["/usr/bin/defaults", "read", "com.ameba.SwiftBar", "PluginDirectory"],
                            text=True, capture_output=True, timeout=5)
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip()).expanduser().absolute()
    raise UsageError("Choose a plugin folder in SwiftBar first, or pass --plugin-dir PATH.")


def managed(path):
    # Never follow a plugin symlink while replacing/removing a managed file.
    return path.is_file() and not path.is_symlink() and MARKER in path.read_text()


def setup(directory, launcher, codex=None, *, no_animation=False):
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / PLUGIN
    if (target.exists() or target.is_symlink()) and not managed(target):
        raise UsageError(f"Refusing to overwrite an unmanaged plugin: {target}")
    args = [str(launcher), "stream"]
    if no_animation:
        args.append("--no-animation")
    if codex:
        args += ["--codex", codex]
    search_path = (str(Path(codex).parent) + ":" if codex else "") + "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
    body = ("#!/bin/sh\n" + MARKER + "\n# <swiftbar.title>Codexbar Lite</swiftbar.title>\n"
            "# <swiftbar.version>" + VERSION + "</swiftbar.version>\n"
            "# <swiftbar.type>streamable</swiftbar.type>\n"
            "# <swiftbar.useTrailingStreamSeparator>true</swiftbar.useTrailingStreamSeparator>\n"
            "export PATH=" + shlex.quote(search_path) + ":\"$PATH\"\nexec " + shlex.join(args) + "\n")
    fd, temporary = tempfile.mkstemp(prefix=".codexbar-", dir=directory)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(body)
        os.chmod(temporary, 0o755)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return target


def uninstall(directory):
    target = directory / PLUGIN
    if not target.exists() and not target.is_symlink():
        return False
    if not managed(target):
        raise UsageError("Refusing to remove an unmanaged plugin.")
    target.unlink()
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description="Codex quota in your macOS menu bar via SwiftBar.")
    parser.add_argument("--version", action="version", version=VERSION)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("menu", "stream", "status", "doctor"):
        command = commands.add_parser(name)
        command.add_argument("--codex", help="Absolute path to a Codex CLI executable")
        if name == "doctor":
            command.add_argument("--live", action="store_true", help="Also request live account limits")
        if name == "stream":
            command.add_argument("--no-animation", action="store_true", help="Skip the startup animation")
        if name in ("menu", "stream"):
            command.add_argument("--demo", action="store_true", help="Render synthetic 52% / 42% data without Codex")
    for name in ("setup", "uninstall"):
        command = commands.add_parser(name)
        command.add_argument("--plugin-dir")
        if name == "setup":
            command.add_argument("--codex")
            command.add_argument("--no-animation", action="store_true", help="Skip the startup animation")
    args = parser.parse_args(argv)
    try:
        if args.command == "setup":
            launcher = os.environ.get("CODEXBAR_LAUNCHER")
            if not launcher or not Path(launcher).is_file():
                raise UsageError("Run setup via the installed codexbar-lite command (see README).")
            executable = find_codex(args.codex)
            target = setup(plugin_directory(args.plugin_dir), launcher, executable, no_animation=args.no_animation)
            print(f"Installed {target}\nOpen SwiftBar; the plugin refreshes every minute.")
        elif args.command == "uninstall":
            removed = uninstall(plugin_directory(args.plugin_dir))
            print("Plugin removed." if removed else "Plugin is already absent.")
        elif args.command == "doctor":
            print(f"Codexbar Lite {VERSION}\nRenderer: {'OK' if renderer_path().is_file() else 'MISSING'}")
            executable = find_codex(args.codex)
            print(f"Codex: {executable}")
            render_image(windows({}), "Light")
            if args.live:
                snapshot = read_limits(executable)
                if all(value is None for _, value, _ in windows(snapshot)):
                    raise UsageError("Account returned no usage windows.")
                print("Live Codex quota: OK")
        elif args.command == "stream":
            def fetch():
                if args.demo:
                    return {"primary": {"usedPercent": 48, "windowDurationMins": 300},
                            "secondary": {"usedPercent": 58, "windowDurationMins": 10080}}
                return read_limits(find_codex(args.codex))
            control = RefreshInput(sys.stdin)
            previous = signal.signal(signal.SIGTERM, stop_stream)
            try:
                run_stream(fetch, os.environ.get("OS_APPEARANCE", "Light"), emit_frame, control.wait,
                           animate=not args.no_animation and not reduce_motion())
            except KeyboardInterrupt:
                pass
            except BrokenPipeError:
                # Prevent a second flush error when stdout has been disconnected.
                sys.stdout = open(os.devnull, "w")
            finally:
                signal.signal(signal.SIGTERM, previous)
                control.close()
        else:
            if args.command == "menu" and args.demo:
                snapshot = {"primary": {"usedPercent": 48, "windowDurationMins": 300},
                            "secondary": {"usedPercent": 58, "windowDurationMins": 10080}}
            else:
                snapshot = read_limits(find_codex(args.codex))
            if args.command == "status":
                print(json.dumps({title: {"remainingPercent": value, "resetsAt": (window or {}).get("resetsAt")}
                                  for title, value, window in windows(snapshot)}, indent=2))
            else:
                print(menu(snapshot, os.environ.get("OS_APPEARANCE", "Light")))
        return 0
    except (UsageError, OSError, ValueError, subprocess.SubprocessError) as error:
        # Do not echo raw server responses or credentials into SwiftBar or logs.
        message = str(error) if isinstance(error, UsageError) else "Local operation failed. Run codexbar-lite doctor."
        if args.command in ("menu", "stream"):
            if args.command == "stream":
                emit_frame(error_menu(error, stream=True))
            else:
                print(error_menu(error))
            return 0
        print(message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
