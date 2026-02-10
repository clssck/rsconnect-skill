#!/usr/bin/env python3
"""Pre-deploy validation for Python apps on Posit Connect (Git-backed).

Checks: manifest.json, requirements.txt, uv, rsconnect-python,
        Python version match, manifest freshness, allow_uv status.

Exit codes: 0 = ready to deploy, 1 = issues found
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
    box_result,
    check_command,
    check_skill_dir_gitignored,
    get_local_python_version,
    get_manifest_allow_uv,
    get_pyproject_requires_python,
    get_python_version_file,
    get_requirements_packages,
    is_exact_python_version,
    parse_manifest_python_version,
    skill_script_path,
)

passed = True
issues = []
warnings = []
script_dir = os.path.dirname(os.path.abspath(__file__))

box_header("PYTHON PRE-DEPLOY CHECK")

# Preliminary: check if skill directory is gitignored
is_ignored, agent_dir = check_skill_dir_gitignored()
if not is_ignored and agent_dir:
    print(f"{SYM_WARN} Skill directory '{agent_dir}/' is not in .gitignore")
    warnings.append(f"Add '{agent_dir}/' to .gitignore to avoid committing agent skill files")
    print()

# Check 1: pyproject.toml exists
print("1. Project file... ", end="")
if os.path.exists("pyproject.toml"):
    requires_py = get_pyproject_requires_python()
    if requires_py:
        print(f"{SYM_CHECK} pyproject.toml (requires-python: {requires_py})")
    else:
        print(f"{SYM_WARN} pyproject.toml found but no requires-python set")
        warnings.append("Add requires-python to pyproject.toml [project] section")
else:
    print(f"{SYM_CROSS} MISSING")
    issues.append(
        f"No pyproject.toml — regenerate manifest to auto-create, or run: uv init"
    )
    passed = False

# Check 2: manifest.json exists
print("2. Manifest file... ", end="")
if os.path.exists("manifest.json"):
    print(f"{SYM_CHECK} Present")
else:
    print(f"{SYM_CROSS} MISSING")
    issues.append(f"Run: python {skill_script_path('regenerate_manifest_py.py')}")
    passed = False

# Check 3: requirements.txt exists
print("3. Requirements file... ", end="")
if os.path.exists("requirements.txt"):
    pkgs = get_requirements_packages("requirements.txt")
    print(f"{SYM_CHECK} Present ({len(pkgs)} packages)")
else:
    print(f"{SYM_CROSS} MISSING")
    issues.append("Run: uv export --no-hashes -o requirements.txt")
    passed = False

# Check 4: uv is installed
print("4. uv installed... ", end="")
if check_command("uv"):
    print(f"{SYM_CHECK} Found")
else:
    print(f"{SYM_CROSS} NOT FOUND")
    issues.append("Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh")
    passed = False

# Check 5: rsconnect-python is available
print("5. rsconnect-python... ", end="")
rsconnect_path = check_command("rsconnect")
if rsconnect_path:
    print(f"{SYM_CHECK} Found")
elif check_command("uvx"):
    print(f"{SYM_WARN} Not installed (uvx available as fallback)")
    warnings.append("Consider: uv tool install rsconnect-python")
else:
    print(f"{SYM_CROSS} NOT FOUND")
    issues.append("Install: uv tool install rsconnect-python")
    passed = False

# Check 6: Python version exact pinning
print("6. Python version pinning... ", end="")
raw_pv = get_python_version_file()
if raw_pv:
    if is_exact_python_version(raw_pv):
        print(f"{SYM_CHECK} {raw_pv} (exact)")
    else:
        # Check pyproject.toml for requires-python context
        requires_py = get_pyproject_requires_python()
        hint = ""
        if requires_py:
            hint = f" (pyproject.toml requires-python: {requires_py})"
        print(f"{SYM_WARN} .python-version says '{raw_pv}' — needs exact major.minor.patch")
        warnings.append(
            f".python-version uses '{raw_pv}' — Posit Connect needs exact version "
            f"(e.g. {raw_pv}.6). Set to the version on your Connect server{hint}"
        )
else:
    print(f"{SYM_WARN} No .python-version file")
    warnings.append("Create .python-version with exact version matching your Connect server (e.g. 3.12.7)")

# Check 7: Python version in manifest matches local
print("7. Python version match... ", end="")
manifest_version = parse_manifest_python_version()
local_version = get_local_python_version()

if manifest_version and local_version:
    if manifest_version == local_version:
        print(f"{SYM_CHECK} {local_version} (exact match)")
    else:
        # Compare major.minor only (patch differences are usually OK)
        manifest_mm = ".".join(manifest_version.split(".")[:2])
        local_mm = ".".join(local_version.split(".")[:2])
        if manifest_mm == local_mm:
            print(f"{SYM_CHECK} {local_version} (manifest: {manifest_version})")
        else:
            print(f"{SYM_WARN} Local {local_version} vs manifest {manifest_version}")
            warnings.append(
                f"Python version mismatch (local {local_mm} vs manifest {manifest_mm}) "
                f"— regenerate manifest if intentional"
            )
elif manifest_version:
    print(f"? Manifest says {manifest_version}, couldn't detect local")
elif os.path.exists("manifest.json"):
    print("? No Python version in manifest")
else:
    print("- Skipped (no manifest)")

# Check 8: Manifest freshness (newer than requirements.txt)
print("8. Manifest freshness... ", end="")
if os.path.exists("manifest.json") and os.path.exists("requirements.txt"):
    manifest_mtime = os.path.getmtime("manifest.json")
    req_mtime = os.path.getmtime("requirements.txt")

    if manifest_mtime >= req_mtime:
        print(f"{SYM_CHECK} Manifest is up to date")
    else:
        print(f"{SYM_WARN} Manifest may be stale (older than requirements.txt)")
        warnings.append(
            f"Consider: python {skill_script_path('regenerate_manifest_py.py')}"
        )
else:
    print("- Skipped (missing files)")

# Check 9: allow_uv in manifest (informational)
print("9. allow_uv in manifest... ", end="")
allow_uv = get_manifest_allow_uv()
if allow_uv is True:
    print(f"{SYM_CHECK} Enabled")
elif allow_uv is False:
    print(f"{SYM_WARN} Explicitly disabled")
    warnings.append("allow_uv is false — Connect will use pip instead of uv")
elif os.path.exists("manifest.json"):
    print(f"{SYM_WARN} Not set (Connect uses server default)")
    warnings.append(
        "Set allow_uv: true in manifest for faster installs — "
        f"run: python {skill_script_path('regenerate_manifest_py.py')}"
    )
else:
    print("- Skipped (no manifest)")

# Summary
box_result(passed)

if passed:
    if warnings:
        print("\nOptional improvements:")
        for w in warnings:
            print(f"  - {w}")
    sys.exit(0)
else:
    print("\nFixes needed:")
    for issue in issues:
        print(f"  - {issue}")
    if warnings:
        print("\nAlso consider:")
        for w in warnings:
            print(f"  - {w}")
    sys.exit(1)
