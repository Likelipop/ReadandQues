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
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DJANGO_ROOT = ROOT / "ReadAndQues"
EXCLUDED_PARTS = {".git", ".venv", "staticfiles", "__pycache__", "node_modules", "dist"}


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
    environment.setdefault("DJANGO_SETTINGS_MODULE", "ReadAndQues.settings.dev")
    environment["PYTHONPATH"] = f"{ROOT}:{DJANGO_ROOT}:{environment.get('PYTHONPATH', '')}"
    run(
        "service characterization tests",
        [
            sys.executable,
            "-m",
            "unittest",
            "service.tests.test_data_integrity",
            "service.tests.test_ai_platform",
            "service.tests.test_grounded_question_ticket",
            "service.tests.test_pdf_parser",
            "service.tests.test_dictionary",
            "service.tests.test_smart_ink_flow",
            "service.tests.test_explained_graph",
            "service.tests.test_explained_streaming",
        ],
        cwd=DJANGO_ROOT,
        env=environment,
    )


def full_checks() -> None:
    environment = os.environ.copy()
    environment.setdefault("DJANGO_SETTINGS_MODULE", "ReadAndQues.settings.dev")
    environment["PYTHONPATH"] = f"{ROOT}:{DJANGO_ROOT}:{environment.get('PYTHONPATH', '')}"
    manage = [sys.executable, "manage.py"]
    run("Django system check", manage + ["check"], cwd=DJANGO_ROOT, env=environment)
    run(
        "Django migration drift",
        manage + ["makemigrations", "--check", "--dry-run"],
        cwd=DJANGO_ROOT,
        env=environment,
    )
    run(
        "service pipelines & services smoke check",
        [
            sys.executable,
            "-c",
            "import django; django.setup(); import service.pipelines; import service.services; import service.selectors",
        ],
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
