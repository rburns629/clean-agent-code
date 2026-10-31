"""Print change metrics for one fixture as JSON. Runs inside the no-network container.

Usage: python3 inspect_run.py <fixture>
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1])
DOCS = re.compile(r"^(AGENTS\.md|CLAUDE\.md|PROJECT_CONTEXT\.md|standards/|templates/)")


def git(*args):
    return subprocess.run(["git", "-c", "safe.directory=*", "-c", "core.fsmonitor=", "-C", str(ROOT),
                           "--no-pager", *args], capture_output=True, text=True).stdout


first = git("rev-list", "--max-parents=0", "HEAD").split()[0]
added = {}
for line in git("diff", "--numstat", "--no-ext-diff", "--no-textconv", first).splitlines():
    plus, _, name = line.split("\t")
    added[name] = int(plus) if plus.isdigit() else 0
untracked = [n for n in git("ls-files", "--others", "--exclude-standard").split() if (ROOT / n).is_file()]
for name in untracked:
    added[name] = len((ROOT / name).read_text(errors="ignore").splitlines())
deleted = git("diff", "--name-only", "--diff-filter=D", first).split()
added = {n: v for n, v in added.items() if "__pycache__" not in n}
test_diff = git("diff", "-U0", first, "--", "tests") + "".join(
    (ROOT / n).read_text(errors="ignore") for n in untracked if n.startswith("tests/"))
print(json.dumps({
    "src_lines_added": sum(v for n, v in added.items() if not n.startswith("tests/") and not DOCS.match(n)),
    "test_lines_added": sum(v for n, v in added.items() if n.startswith("tests/")),
    "test_methods_added": len(re.findall(r"^\+?\s*def test_", test_diff, re.M)),
    "docs_changed": sorted(n for n in [*added, *deleted] if DOCS.match(n)),
    "deleted": deleted,
    "legacy_exists": (ROOT / "reports/legacy.py").exists(),
    "readme": (ROOT / "README.md").read_text(errors="ignore") if (ROOT / "README.md").exists() else "",
}))
