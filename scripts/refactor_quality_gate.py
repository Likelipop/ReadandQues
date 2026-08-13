#!/usr/bin/env python3
"""Repeatable quality gates for the staged service refactor.

The default gate is intentionally infrastructure-free so it can run on every
commit. ``--full`` adds Django configuration, migration-drift, and orchestrator
import checks and therefore requires the locked dependencies and local services.
"""

from __future__ import annotations

import argparse
import ast
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
DJANGO_ROOT = ROOT / "ReadAndQues"
EXCLUDED_PARTS = {".git", ".venv", "staticfiles", "__pycache__"}


def run(label: str, command: list[str], *, cwd: Path = ROOT, env=None) -> None:
    print(f"[quality] {label}")
    completed = subprocess.run(command, cwd=cwd, env=env, check=False)
    if completed.returncode:
        raise SystemExit(
            f"[quality] FAILED: {label} (exit code {completed.returncode})"
        )


def check_python_syntax() -> None:
    print("[quality] Python syntax")
    failures = []
    checked = 0
    for path in ROOT.rglob("*.py"):
        if any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        checked += 1
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError) as error:
            failures.append(f"{path.relative_to(ROOT)}: {error}")
    if failures:
        raise SystemExit("[quality] FAILED: Python syntax\n" + "\n".join(failures))
    print(f"[quality] parsed {checked} Python files")


def check_merge_markers() -> None:
    print("[quality] unresolved merge markers")
    markers = ("<<<<<<< ", "=======", ">>>>>>> ")
    failures = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        if path.suffix not in {".py", ".md", ".html", ".js", ".toml", ".yaml", ".yml"}:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(lines, start=1):
            if any(line.startswith(marker) for marker in markers):
                failures.append(f"{path.relative_to(ROOT)}:{number}")
    if failures:
        raise SystemExit(
            "[quality] FAILED: unresolved merge markers\n" + "\n".join(failures)
        )


def isolated_tests() -> None:
    environment = os.environ.copy()
    environment.setdefault("DJANGO_SETTINGS_MODULE", "ReadAndQues.settings")
    run(
        "legacy characterization tests",
        [
            sys.executable,
            "-m",
            "unittest",
            "service.tests.test_pipeline_engine",
            "service.tests.test_application_flows",
            "service.tests.test_data_integrity",
            "service.tests.test_typed_orchestration",
            "service.tests.test_ai_platform",
            "service.tests.test_grounded_question_ticket",
            "service.tests.test_operations_cutover",
        ],
        cwd=DJANGO_ROOT,
        env=environment,
    )


def full_checks() -> None:
    environment = os.environ.copy()
    environment.setdefault("DJANGO_SETTINGS_MODULE", "ReadAndQues.settings")
    manage = [sys.executable, "manage.py"]
    run("Django system check", manage + ["check"], cwd=DJANGO_ROOT, env=environment)
    run(
        "Django migration drift",
        manage + ["makemigrations", "--check", "--dry-run"],
        cwd=DJANGO_ROOT,
        env=environment,
    )
    run(
        "orchestrator import smoke check",
        [sys.executable, "-c", "import service.orchestrator"],
        cwd=DJANGO_ROOT,
        env=environment,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--full",
        action="store_true",
        help="also run checks requiring locked dependencies and local services",
    )
    arguments = parser.parse_args()

    check_python_syntax()
    check_merge_markers()
    isolated_tests()
    if arguments.full:
        full_checks()
    print("[quality] PASS")


if __name__ == "__main__":
    main()
