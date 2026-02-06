#!/usr/bin/env python3
"""Diagnose Python deployment issues for Posit Connect.

Reports: Python/uv/rsconnect versions, key files, manifest details,
         package counts, allow_uv status.

Exit codes: 0 = healthy, 1 = issues found
"""

import os
import sys

# Add lib/ to path for shared utilities
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))

from py_utils import (
    SYM_CHECK,
    SYM_CROSS,
    SYM_WARN,
    box_header,
    check_command,
    check_skill_dir_gitignored,
    get_local_python_version,
    get_manifest_allow_uv,
    get_manifest_content_type,
    get_manifest_entrypoint,
    get_requirements_packages,
    parse_manifest_python_version,
    run_command,
    skill_script_path,
)

# Parse arguments
args = sys.argv[1:]
verbose = "--verbose" in args or "-v" in args
help_requested = "--help" in args or "-h" in args

if help_requested:
    print("Usage: python diagnose_py.py [OPTIONS]\n")
    print("Options:")
    print("  --verbose, -v  Include detailed manifest and requirements output")
    print("  --help, -h     Show this help message")
    print("\nThis script checks:")
    print("  - Python, uv, rsconnect-python versions")
    print("  - Key files (requirements.txt, manifest.json, pyproject.toml)")
    print("  - Manifest content type and entrypoint")
    print("  - Package count in requirements.txt")
    print("  - allow_uv status in manifest")
    sys.exit(0)

issues = []

box_header("PYTHON DEPLOYMENT DIAGNOSTICS")

# Section 1: Environment info
print("--- Environment ---")

# Python version
local_version = get_local_python_version()
print(f"Python version: {local_version}")
print(f"Python path: {sys.executable}")
print(f"Working dir: {os.getcwd()}")

# uv version
if check_command("uv"):
    result = run_command(["uv", "--version"])
    if result.returncode == 0:
        print(f"uv version: {result.stdout.strip()}")
    else:
        print(f"uv: installed (couldn't get version)")
else:
    print("uv: NOT INSTALLED")
    issues.append("uv not installed — install: curl -LsSf https://astral.sh/uv/install.sh | sh")

# rsconnect-python version
if check_command("rsconnect"):
    result = run_command(["rsconnect", "version"])
    if result.returncode == 0:
        print(f"rsconnect-python: {result.stdout.strip()}")
    else:
        print("rsconnect-python: installed (couldn't get version)")
elif check_command("uvx"):
    print(f"{SYM_WARN} rsconnect-python: not installed (uvx available as fallback)")
else:
    print("rsconnect-python: NOT INSTALLED")
    issues.append("rsconnect-python not installed — install: uv tool install rsconnect-python")

print()

# Gitignore check
print("--- Gitignore ---")
is_ignored, agent_dir = check_skill_dir_gitignored()
if agent_dir:
    if is_ignored:
        print(f"{SYM_CHECK} {agent_dir}/ is in .gitignore")
    else:
        print(f"{SYM_WARN} {agent_dir}/ is NOT in .gitignore")
        issues.append(f"Add '{agent_dir}/' to .gitignore to avoid committing agent skill files")
else:
    print("Skill not under a recognized agent directory — skipped")

print()

# Section 2: Key files
print("--- Key Files ---")
files = [
    "requirements.txt",
    "manifest.json",
    "pyproject.toml",
    ".python-version",
    "uv.lock",
    ".rscignore",
]

for f in files:
    if os.path.exists(f):
        from datetime import datetime
        mtime = os.path.getmtime(f)
        mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        print(f"{SYM_CHECK} {f} ( {mtime_str} )")
    else:
        print(f"{SYM_CROSS} {f} — missing")
        if f == "manifest.json":
            issues.append("manifest.json missing — run: rsconnect write-manifest <type> .")
        elif f == "requirements.txt":
            issues.append("requirements.txt missing — run: uv export --no-hashes -o requirements.txt")

print()

# Section 3: Manifest details
print("--- Manifest Details ---")
if os.path.exists("manifest.json"):
    manifest_py_ver = parse_manifest_python_version()
    content_type = get_manifest_content_type()
    entrypoint = get_manifest_entrypoint()
    allow_uv = get_manifest_allow_uv()

    print(f"Python version: {manifest_py_ver or 'not set'}")
    print(f"Content type: {content_type or 'not set'}")
    print(f"Entrypoint: {entrypoint or 'not set'}")

    if allow_uv is True:
        print(f"allow_uv: {SYM_CHECK} enabled")
    elif allow_uv is False:
        print(f"allow_uv: {SYM_WARN} explicitly disabled")
    else:
        print(f"allow_uv: {SYM_WARN} not set (server default)")
        issues.append(
            "allow_uv not set in manifest — "
            f"run: python {skill_script_path('regenerate_manifest_py.py')}"
        )

    # Version match check
    if manifest_py_ver and local_version:
        manifest_mm = ".".join(manifest_py_ver.split(".")[:2])
        local_mm = ".".join(local_version.split(".")[:2])
        if manifest_mm != local_mm:
            print(f"{SYM_WARN} Version mismatch: local {local_version} vs manifest {manifest_py_ver}")
            issues.append(
                f"Python version mismatch (local {local_mm} vs manifest {manifest_mm})"
            )
else:
    print("No manifest.json found")

print()

# Section 4: Requirements details
print("--- Requirements ---")
if os.path.exists("requirements.txt"):
    pkgs = get_requirements_packages("requirements.txt")
    print(f"Package count: {len(pkgs)}")

    if verbose and pkgs:
        print("\nPackages:")
        for pkg in pkgs:
            print(f"  - {pkg}")
else:
    print("No requirements.txt found")

print()

# Section 5: pyproject.toml check
print("--- Project Configuration ---")
if os.path.exists("pyproject.toml"):
    print(f"{SYM_CHECK} pyproject.toml found")
    if verbose:
        try:
            with open("pyproject.toml") as f:
                content = f.read()
            # Show project name and version if present
            for line in content.split("\n"):
                line_stripped = line.strip()
                if line_stripped.startswith("name") or line_stripped.startswith("version"):
                    print(f"  {line_stripped}")
        except OSError:
            pass
else:
    print(f"{SYM_WARN} No pyproject.toml — uv projects require this")

print()

# Summary
print("=== Summary ===")
if not issues:
    print(f"{SYM_CHECK} No issues detected!")
    print(f"\nReady to deploy. Run pre-deploy check to confirm:")
    print(f"  python {skill_script_path('pre_deploy_check_py.py')}")
    sys.exit(0)
else:
    print(f"{SYM_CROSS} {len(issues)} issue(s) found:")
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")
    print(f"\nSuggested fixes:")
    print(f"  - Regenerate manifest: python {skill_script_path('regenerate_manifest_py.py')}")
    print(f"  - Full pre-deploy check: python {skill_script_path('pre_deploy_check_py.py')}")
    sys.exit(1)
