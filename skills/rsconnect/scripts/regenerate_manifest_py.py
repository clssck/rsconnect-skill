#!/usr/bin/env python3
"""Regenerate manifest.json for Python apps on Posit Connect (Git-backed).

Steps:
1. Detect content type (FastAPI, Flask, etc.) or use --type flag
2. Export requirements.txt via uv
3. Run rsconnect write-manifest
4. Patch allow_uv: true into manifest.json
5. Verify and report

Exit codes: 0 = success, 1 = failed
"""

import argparse
import json
import os
import re
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
    generate_pyproject_toml,
    get_local_python_version,
    get_python_version_file,
    is_exact_python_version,
    run_command,
    skill_script_path,
)

CONTENT_TYPES = ["api", "fastapi", "flask", "dash", "streamlit", "bokeh", "notebook"]


def detect_content_type() -> str | None:
    """Auto-detect Python content type from project files.

    Looks for common entrypoint files and framework imports.
    """
    # Check common entrypoint files
    candidates = ["app.py", "main.py", "api.py", "application.py", "server.py"]
    entrypoint = None
    for name in candidates:
        if os.path.exists(name):
            entrypoint = name
            break

    if entrypoint is None:
        # Check for notebooks
        for f in os.listdir("."):
            if f.endswith(".ipynb"):
                return "notebook"
        return None

    # Read the entrypoint and check imports
    try:
        with open(entrypoint) as f:
            content = f.read()
    except OSError:
        return "api"  # Safe default

    # Check for framework-specific imports
    if re.search(r"from\s+fastapi\s+import|import\s+fastapi", content):
        return "fastapi"
    if re.search(r"from\s+flask\s+import|import\s+flask", content):
        return "flask"
    if re.search(r"from\s+dash\s+import|import\s+dash", content):
        return "dash"
    if re.search(r"from\s+streamlit|import\s+streamlit", content):
        return "streamlit"
    if re.search(r"from\s+bokeh|import\s+bokeh", content):
        return "bokeh"
    if re.search(r"from\s+shiny\s+import|import\s+shiny", content):
        return "api"  # Shiny for Python uses api type

    # Default: generic API
    return "api"


def patch_allow_uv(manifest_path: str = "manifest.json") -> bool:
    """Patch allow_uv: true into manifest.json python.package_manager section.

    Returns True if patched successfully, False on error.
    """
    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"  {SYM_CROSS} Failed to read manifest: {e}")
        return False

    python_section = manifest.get("python")
    if python_section is None:
        print(f"  {SYM_WARN} No python section in manifest — skipping allow_uv patch")
        return True  # Not an error, just not applicable

    if "package_manager" not in python_section:
        python_section["package_manager"] = {}

    python_section["package_manager"]["allow_uv"] = True

    try:
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
            f.write("\n")  # Trailing newline
    except OSError as e:
        print(f"  {SYM_CROSS} Failed to write manifest: {e}")
        return False

    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regenerate manifest.json for Python apps on Posit Connect"
    )
    parser.add_argument(
        "--type",
        choices=CONTENT_TYPES,
        default=None,
        help="Content type (auto-detected if not specified)",
    )
    parser.add_argument(
        "--no-uv-export",
        action="store_true",
        help="Skip uv export step (use existing requirements.txt)",
    )
    parser.add_argument(
        "--no-allow-uv",
        action="store_true",
        help="Don't patch allow_uv: true into manifest",
    )
    args = parser.parse_args()

    box_header("REGENERATE PYTHON MANIFEST")

    # Step 1: Check prerequisites and determine rsconnect command
    if not check_command("rsconnect") and not check_command("uvx"):
        print(f"{SYM_CROSS} rsconnect-python not installed and uvx not available")
        print("Install: uv tool install rsconnect-python")
        sys.exit(1)

    # Determine target Python version from .python-version or current interpreter
    target_python = get_local_python_version()

    # Warn if .python-version uses a short version (e.g. 3.13 instead of 3.13.6)
    raw_pv = get_python_version_file()
    if raw_pv and not is_exact_python_version(raw_pv):
        print(f"{SYM_WARN} .python-version says '{raw_pv}' — needs exact major.minor.patch")
        print(f"  Set to the version on your Connect server (e.g. {raw_pv}.6)")

    # Build rsconnect command — use uvx --python to ensure the manifest
    # gets stamped with the correct Python version (matching .python-version).
    # Note: the package is "rsconnect-python" but the executable is "rsconnect",
    # so uvx needs --from rsconnect-python rsconnect.
    if check_command("uvx"):
        rsconnect_cmd = [
            "uvx", "--python", target_python,
            "--from", "rsconnect-python", "rsconnect",
        ]
        print(f"Target Python: {target_python} (via uvx --python)")
    elif check_command("rsconnect"):
        rsconnect_cmd = ["rsconnect"]
        print(f"Target Python: {target_python} (using installed rsconnect)")
    else:
        print(f"{SYM_CROSS} rsconnect-python not installed and uvx not available")
        sys.exit(1)

    # Step 2: Detect content type
    content_type = args.type
    if content_type is None:
        print("Detecting content type... ", end="")
        content_type = detect_content_type()
        if content_type:
            print(f"{SYM_CHECK} {content_type}")
        else:
            print(f"{SYM_CROSS} Could not auto-detect")
            print("Specify with: --type [api|fastapi|flask|dash|streamlit|bokeh|notebook]")
            sys.exit(1)
    else:
        print(f"Content type: {content_type}")

    # Step 3: Export requirements.txt via uv
    if not args.no_uv_export:
        print("\nExporting requirements.txt... ", end="")
        if not check_command("uv"):
            print(f"{SYM_CROSS} uv not found")
            print("Install uv or use --no-uv-export with existing requirements.txt")
            sys.exit(1)

        # Generate pyproject.toml if missing (uv export needs it)
        if not os.path.exists("pyproject.toml"):
            print(f"{SYM_WARN} no pyproject.toml")
            print("  Generating minimal pyproject.toml... ", end="")
            content = generate_pyproject_toml(python_version=target_python)
            try:
                with open("pyproject.toml", "w") as f:
                    f.write(content)
                print(f"{SYM_CHECK}")
                print(f"  {SYM_WARN} Review pyproject.toml and adjust dependencies as needed")
            except OSError as e:
                print(f"{SYM_CROSS} Failed: {e}")
                print("  Create manually or use --no-uv-export with existing requirements.txt")
                sys.exit(1)

        result = run_command(["uv", "export", "--no-hashes", "-o", "requirements.txt"])
        if result.returncode == 0:
            print(f"{SYM_CHECK}")
        else:
            print(f"{SYM_CROSS}")
            print(f"  Error: {result.stderr.strip()}")
            sys.exit(1)
    else:
        print("\nSkipping uv export (using existing requirements.txt)")
        if not os.path.exists("requirements.txt"):
            print(f"  {SYM_CROSS} requirements.txt not found")
            sys.exit(1)

    # Step 4: Generate manifest via rsconnect write-manifest
    # Map content types to rsconnect write-manifest types
    rsconnect_type = content_type
    if content_type == "flask":
        rsconnect_type = "api"  # Flask uses generic api type

    print(f"\nGenerating manifest.json ({rsconnect_type})... ", end="")
    cmd = rsconnect_cmd + ["write-manifest", rsconnect_type, ".", "--overwrite"]
    result = run_command(cmd)

    if result.returncode == 0:
        print(f"{SYM_CHECK}")
    else:
        print(f"{SYM_CROSS}")
        print(f"  Error: {result.stderr.strip()}")
        box_result(False)
        print("\nCommon causes:")
        print("  - Missing entrypoint (app.py, main.py)")
        print("  - Wrong content type (try --type flag)")
        print("  - rsconnect-python not installed (uv tool install rsconnect-python)")
        sys.exit(1)

    # Step 5: Patch allow_uv into manifest
    if not args.no_allow_uv:
        print("Patching allow_uv: true... ", end="")
        if patch_allow_uv():
            print(f"{SYM_CHECK}")
        else:
            print(f"{SYM_WARN} Failed (manifest still usable without it)")

    # Step 6: Verify manifest was created
    if os.path.exists("manifest.json"):
        box_result(True)
        print("\nmanifest.json regenerated successfully")
        print("\nNext steps:")
        print(f"  1. Run pre-deploy check: python {skill_script_path('pre_deploy_check_py.py')}")
        print("  2. Commit: git add manifest.json requirements.txt && git commit -m 'chore: update manifest'")
        print("  3. Push to trigger deployment")
        sys.exit(0)
    else:
        box_result(False)
        print("\nrsconnect write-manifest succeeded but manifest.json not found")
        sys.exit(1)


if __name__ == "__main__":
    main()
