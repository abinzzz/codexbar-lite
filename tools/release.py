#!/usr/bin/env python3
"""Create a source release and a Homebrew tap formula for that exact archive."""
import argparse
import ast
import gzip
import hashlib
from pathlib import Path
import re
import tarfile

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument("--repository", required=True, help="GitHub OWNER/REPO")
p.add_argument("--output", type=Path, default=ROOT / "dist")
a = p.parse_args()
if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", a.repository):
    p.error("repository must be OWNER/REPO")
module = ast.parse((ROOT / "src/codexbar.py").read_text())
version = next(ast.literal_eval(n.value) for n in module.body if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == "VERSION" for t in n.targets))
a.output.mkdir(parents=True, exist_ok=True)
archive = a.output / f"codexbar-lite-{version}.tar.gz"
include = ["src", "tests", "tools", "docs", "Formula", ".github", ".gitignore", "Makefile", "README.md", "LICENSE", "CHANGELOG.md"]
files = []
for name in include:
    path = ROOT / name
    files.extend(path.rglob("*") if path.is_dir() else [path])
with archive.open("wb") as stream, gzip.GzipFile(filename="", mode="wb", fileobj=stream, mtime=0) as zipped:
    with tarfile.open(fileobj=zipped, mode="w") as tar:
        for path in sorted(files):
            if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            info = tar.gettarinfo(str(path), arcname=f"codexbar-lite-{version}/{path.relative_to(ROOT)}")
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = 0
            with path.open("rb") as data:
                tar.addfile(info, data)
sha = hashlib.sha256(archive.read_bytes()).hexdigest()
formula = (ROOT / "Formula/codexbar-lite.rb.in").read_text().replace("@REPOSITORY@", a.repository).replace("@VERSION@", version).replace("@SHA256@", sha)
(a.output / "codexbar-lite.rb").write_text(formula)
(a.output / "SHA256SUMS").write_text(f"{sha}  {archive.name}\n")
print(f"Created {archive}\nSHA256: {sha}\nFormula: {a.output / 'codexbar-lite.rb'}")
