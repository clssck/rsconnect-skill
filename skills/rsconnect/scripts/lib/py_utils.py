"""Shared utilities for rsconnect Python helper scripts.

Mirrors the patterns from parse_utils.R:
- Unicode symbols for consistent output
- Box-drawing header/result formatting
- Skill root path resolution ($SKILL_DIR equivalent)
- Command availability checks
- Manifest and requirements.txt parsing
"""

import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Force UTF-8 stdout/stderr on Windows where the default codepage (cp1252)
# can't encode box-drawing characters or check-mark symbols.
if sys.platform == "win32":
    if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding.lower().replace("-", "") != "utf8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if not isinstance(sys.stderr, io.TextIOWrapper) or sys.stderr.encoding.lower().replace("-", "") != "utf8":
        try:
            sys.stderr.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Unicode symbols for consistent output (matches R scripts)
SYM_CHECK = "\u2713"  # check mark
SYM_CROSS = "\u2717"  # cross mark
SYM_WARN = "\u26a0"   # warning sign


def box_header(title: str, width: int = 40) -> None:
    """Print a boxed header for script output (matches R box_header)."""
    title = title[:width - 4]
    padding = width - len(title) - 4

    print()
    print("\u2554" + "\u2550" * (width - 2) + "\u2557")
    print("\u2551  " + title + " " * padding + "\u2551")
    print("\u255a" + "\u2550" * (width - 2) + "\u255d")
    print()


def box_result(success: bool, width: int = 40) -> None:
    """Print a boxed result (matches R box_result)."""
    print()
    print("\u2554" + "\u2550" * (width - 2) + "\u2557")
    if success:
        msg = f"{SYM_CHECK} READY TO DEPLOY"
    else:
        msg = f"{SYM_CROSS} ISSUES FOUND"
    padding = max(0, width - len(msg) - 4)
    print("\u2551  " + msg + " " * padding + "\u2551")
    print("\u255a" + "\u2550" * (width - 2) + "\u255d")


def get_script_dir() -> Path:
    """Get the directory of the currently running script.

    Uses the *unresolved* argv[0] so the returned path matches
    what the user typed (e.g. .cursor/skills/... not a resolved symlink).
    """
    if sys.argv[0]:
        script_path = Path(sys.argv[0]).absolute()
        if script_path.is_file():
            return script_path.parent
    return Path.cwd()


def get_skill_root(from_dir: Path | None = None) -> Path:
    """Get the skill root directory (agent-agnostic).

    Walks up from scripts/lib/ -> scripts/ -> skill root.
    Works regardless of where the skill is installed.
    """
    if from_dir is None:
        from_dir = get_script_dir()

    d = from_dir.absolute()
    if d.name == "lib":
        d = d.parent  # lib/ -> scripts/
    if d.name == "scripts":
        d = d.parent  # scripts/ -> skill root
    return d


def skill_script_path(script_name: str, from_dir: Path | None = None) -> str:
    """Build a display-friendly path to a skill script.

    Uses the unresolved (non-symlink-followed) path from argv[0] so the
    output matches the actual directory the user sees on disk
    (e.g. .cursor/skills/... not .agents/skills/...).
    """
    root = get_skill_root(from_dir)
    full_path = root / "scripts" / script_name

    # Try to make it relative to cwd
    try:
        return str(full_path.relative_to(Path.cwd()))
    except ValueError:
        return str(full_path)


def check_command(cmd: str) -> str | None:
    """Check if a CLI command is available.

    Returns the path to the command, or None if not found.
    """
    return shutil.which(cmd)


def run_command(cmd: list[str], capture: bool = True) -> subprocess.CompletedProcess:
    """Run a subprocess command, returning the result.

    Raises subprocess.CalledProcessError on non-zero exit.
    """
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        check=False,
    )


def parse_manifest(manifest_path: str = "manifest.json") -> dict | None:
    """Parse manifest.json, returning the parsed dict or None on error."""
    try:
        with open(manifest_path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def parse_manifest_python_version(manifest_path: str = "manifest.json") -> str | None:
    """Read the Python version from manifest.json.

    Returns version string (e.g. '3.11.5') or None.
    """
    manifest = parse_manifest(manifest_path)
    if manifest is None:
        return None
    python_section = manifest.get("python", {})
    return python_section.get("version")


def get_manifest_content_type(manifest_path: str = "manifest.json") -> str | None:
    """Read the content type from manifest.json metadata."""
    manifest = parse_manifest(manifest_path)
    if manifest is None:
        return None
    metadata = manifest.get("metadata", {})
    return metadata.get("content_type") or metadata.get("appmode")


def get_manifest_entrypoint(manifest_path: str = "manifest.json") -> str | None:
    """Read the entrypoint from manifest.json metadata."""
    manifest = parse_manifest(manifest_path)
    if manifest is None:
        return None
    metadata = manifest.get("metadata", {})
    return metadata.get("entrypoint")


def get_manifest_allow_uv(manifest_path: str = "manifest.json") -> bool | None:
    """Check if allow_uv is set in manifest.json.

    Returns True/False if explicitly set, None if field is missing.
    """
    manifest = parse_manifest(manifest_path)
    if manifest is None:
        return None
    python_section = manifest.get("python", {})
    pkg_manager = python_section.get("package_manager", {})
    if "allow_uv" in pkg_manager:
        return pkg_manager["allow_uv"]
    return None


def get_requirements_packages(req_path: str = "requirements.txt") -> list[str]:
    """Parse requirements.txt and return list of package specs.

    Skips comments, blank lines, and option lines (e.g. --index-url).
    """
    packages = []
    try:
        with open(req_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                packages.append(line)
    except FileNotFoundError:
        pass
    return packages


def get_local_python_version() -> str | None:
    """Get the local Python major.minor.patch version.

    Checks .python-version file first, then falls back to sys.version_info.
    """
    # Check .python-version file (used by pyenv, uv, etc.)
    pv_file = Path(".python-version")
    if pv_file.exists():
        version = pv_file.read_text().strip()
        if version:
            return version

    # Fall back to running Python version
    info = sys.version_info
    return f"{info.major}.{info.minor}.{info.micro}"
