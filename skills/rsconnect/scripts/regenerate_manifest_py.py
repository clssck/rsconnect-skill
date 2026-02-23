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


def _parse_pyproject() -> dict | None:
    if not os.path.exists("pyproject.toml"):
        return None
    try:
        import tomllib
    except ImportError:
        return None
    try:
        with open("pyproject.toml", "rb") as f:
            return tomllib.load(f)
    except Exception:
        return None


def _parse_pyproject_name() -> str | None:
    data = _parse_pyproject()
    if data:
        name = data.get("project", {}).get("name")
        if name:
            return name
    try:
        in_project = False
        with open("pyproject.toml") as f:
            for line in f:
                line = line.strip()
                if line.startswith("["):
                    in_project = line == "[project]"
                    continue
                if not in_project or not line.startswith("name"):
                    continue
                _, _, value = line.partition("=")
                value = value.strip().strip('"').strip("'")
                if value:
                    return value
    except OSError:
        pass
    return None


def _parse_pyproject_entrypoints() -> list[str]:
    def add_module(target: list[str], value: str | None) -> None:
        if not value:
            return
        module = value.split(":", 1)[0].strip()
        if module and module not in target:
            target.append(module)

    modules: list[str] = []
    data = _parse_pyproject()
    if data:
        project = data.get("project", {})
        scripts = project.get("scripts", {})
        if isinstance(scripts, dict):
            for value in scripts.values():
                if isinstance(value, str):
                    add_module(modules, value)
        entry_points = project.get("entry-points") or project.get("entry_points") or {}
        if isinstance(entry_points, dict):
            for group in entry_points.values():
                if isinstance(group, dict):
                    for value in group.values():
                        if isinstance(value, str):
                            add_module(modules, value)
        if modules:
            return modules

    if not os.path.exists("pyproject.toml"):
        return modules

    try:
        in_section = False
        with open("pyproject.toml") as f:
            for line in f:
                line = line.strip()
                if line.startswith("["):
                    in_section = line.startswith("[project.scripts]") or line.startswith("[project.entry-points.")
                    continue
                if not in_section or "=" not in line:
                    continue
                _, _, value = line.partition("=")
                value = value.strip().strip('"').strip("'")
                add_module(modules, value)
    except OSError:
        pass

    return modules


def _module_to_paths(module: str) -> list[str]:
    rel = module.replace(".", os.sep)
    return [f"{rel}.py", os.path.join(rel, "__init__.py")]


def detect_content_type() -> str | None:
    """Auto-detect Python content type from project files.

    Looks for common entrypoint files and framework imports.
    """
    candidates = [
        "app.py",
        "main.py",
        "api.py",
        "application.py",
        "server.py",
        "wsgi.py",
        "asgi.py",
    ]
    search_dirs: list[str] = []
    seen_dirs: set[str] = set()

    def add_dir(path: str) -> None:
        if not path:
            return
        norm = os.path.normpath(path)
        if norm in seen_dirs:
            return
        if os.path.isdir(norm):
            search_dirs.append(norm)
            seen_dirs.add(norm)

    add_dir(".")
    add_dir("src")

    project_name = _parse_pyproject_name()
    if project_name:
        normalized = project_name.replace("-", "_")
        add_dir(normalized)
        add_dir(os.path.join("src", normalized))

    for base in [".", "src"]:
        if not os.path.isdir(base):
            continue
        for entry in os.listdir(base):
            if entry.startswith(".") or entry in {"__pycache__", ".venv", "venv", ".git"}:
                continue
            path = os.path.join(base, entry)
            if os.path.isdir(path) and os.path.isfile(os.path.join(path, "__init__.py")):
                add_dir(path)

    candidate_paths: list[str] = []
    seen_paths: set[str] = set()

    def add_path(path: str) -> None:
        if not path or path in seen_paths:
            return
        if os.path.exists(path):
            candidate_paths.append(path)
            seen_paths.add(path)

    for base in search_dirs:
        for name in candidates:
            add_path(os.path.join(base, name))

    for module in _parse_pyproject_entrypoints():
        for rel in _module_to_paths(module):
            add_path(rel)
            add_path(os.path.join("src", rel))

    if not candidate_paths:
        for base in (".", "src", "notebooks"):
            if not os.path.isdir(base):
                continue
            for entry in os.listdir(base):
                if entry.endswith(".ipynb"):
                    return "notebook"
        return None

    for entrypoint in candidate_paths:
        try:
            with open(entrypoint, encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError:
            continue

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
    raw_pv = get_python_version_file()
    target_python = get_local_python_version()

    # Ensure exact patch version for Connect; use interpreter when it matches
    if raw_pv and not is_exact_python_version(raw_pv):
        interp_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        raw_mm = ".".join(raw_pv.split(".")[:2])
        interp_mm = f"{sys.version_info.major}.{sys.version_info.minor}"
        if raw_mm == interp_mm:
            target_python = interp_version
            print(
                f"{SYM_WARN} .python-version says '{raw_pv}' — using interpreter {interp_version} (exact)"
            )
            print("  Update .python-version to the exact patch version on your Connect server")
        else:
            print(
                f"{SYM_CROSS} .python-version says '{raw_pv}' but interpreter is {interp_version}"
            )
            print("  Set .python-version to an exact patch version installed on your Connect server")
            sys.exit(1)


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
