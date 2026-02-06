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
    get_local_python_version,
    get_manifest_allow_uv,
    get_requirements_packages,
    parse_manifest_python_version,
    skill_script_path,
)

passed = True
issues = []
warnings = []
script_dir = os.path.dirname(os.path.abspath(__file__))

box_header("PYTHON PRE-DEPLOY CHECK")

# Check 1: manifest.json exists
print("1. Manifest file... ", end="")
if os.path.exists("manifest.json"):
    print(f"{SYM_CHECK} Present")
else:
    print(f"{SYM_CROSS} MISSING")
    issues.append(f"Run: python {skill_script_path('regenerate_manifest_py.py')}")
    passed = False

# Check 2: requirements.txt exists
print("2. Requirements file... ", end="")
if os.path.exists("requirements.txt"):
    pkgs = get_requirements_packages("requirements.txt")
    print(f"{SYM_CHECK} Present ({len(pkgs)} packages)")
else:
    print(f"{SYM_CROSS} MISSING")
    issues.append("Run: uv export --no-hashes -o requirements.txt")
    passed = False

# Check 3: uv is installed
print("3. uv installed... ", end="")
if check_command("uv"):
    print(f"{SYM_CHECK} Found")
else:
    print(f"{SYM_CROSS} NOT FOUND")
    issues.append("Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh")
    passed = False

# Check 4: rsconnect-python is available
print("4. rsconnect-python... ", end="")
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

# Check 5: Python version in manifest matches local
print("5. Python version match... ", end="")
manifest_version = parse_manifest_python_version()
local_version = get_local_python_version()

if manifest_version and local_version:
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

# Check 6: Manifest freshness (newer than requirements.txt)
print("6. Manifest freshness... ", end="")
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

# Check 7: allow_uv in manifest (informational)
print("7. allow_uv in manifest... ", end="")
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
