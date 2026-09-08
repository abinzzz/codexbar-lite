#!/usr/bin/env python3
"""Build and install into an explicit prefix; never modifies SwiftBar preferences."""
import argparse
import platform
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument("--prefix", type=Path, required=True)
p.add_argument("--python", default=sys.executable)
p.add_argument("--launcher-prefix", type=Path, help="Stable Homebrew opt prefix for upgrades")
a = p.parse_args()
if platform.system() != "Darwin" or platform.machine() != "arm64":
    p.error("Codexbar Lite requires an Apple Silicon (M-series) Mac. Run from a native ARM64 terminal/Python.")
prefix = a.prefix.expanduser().absolute()
lib = prefix / "libexec"
lib.mkdir(parents=True, exist_ok=True)
(prefix / "bin").mkdir(exist_ok=True)
subprocess.run(["/usr/bin/swiftc", "-O", "-target", "arm64-apple-macos13.0", "-module-cache-path", str(ROOT / ".build/module-cache"),
                str(ROOT / "src/renderer.swift"), "-o", str(lib / "usage-renderer")], check=True)
shutil.copy2(ROOT / "src/codexbar.py", lib / "codexbar.py")
launcher = (a.launcher_prefix or prefix) / "bin/codexbar-lite"
script = prefix / "bin/codexbar-lite"
script.write_text("#!/bin/sh\nexport CODEXBAR_LAUNCHER=" + shlex.quote(str(launcher)) +
                  "\nexec " + shlex.join([a.python, str(lib / "codexbar.py")]) + ' "$@"\n')
script.chmod(0o755)
print(f"Installed {script}")
