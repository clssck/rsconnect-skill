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
import re
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


def check_skill_dir_gitignored() -> tuple[bool, str | None]:
    """Check if the agent skill directory is listed in .gitignore.

    Detects the top-level agent directory (e.g. .cursor, .agents, .claude)
    from the running script's path, then checks if .gitignore covers it.

    Returns (is_ignored, agent_dir_name) where agent_dir_name is the
    directory that should be gitignored (e.g. '.cursor'), or None if
    the skill isn't installed under a recognizable agent directory.
    """
    skill_root = get_skill_root()
    try:
        rel = skill_root.relative_to(Path.cwd())
    except ValueError:
        return True, None  # Can't determine — skip the check

    # The agent dir is the first component (e.g. ".cursor" from ".cursor/skills/rsconnect")
    parts = rel.parts
    if not parts:
        return True, None

    agent_dir = parts[0]  # e.g. ".cursor", ".agents", ".claude"
    if not agent_dir.startswith("."):
        return True, None  # Not a hidden agent dir — skip

    # Check .gitignore
    gitignore_path = Path(".gitignore")
    if not gitignore_path.exists():
        return False, agent_dir

    gitignore_content = gitignore_path.read_text()
    agent_pattern = re.compile(rf"(^|.*/){re.escape(agent_dir)}(/|$)")
    # Check for the directory with or without trailing slash or common glob patterns
    for line in gitignore_content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        if line in (agent_dir, agent_dir + "/", f"/{agent_dir}", f"/{agent_dir}/"):
            return True, agent_dir
        normalized = line.rstrip("/")
        if normalized in (agent_dir, f"/{agent_dir}"):
            return True, agent_dir
        if agent_pattern.search(line):
            return True, agent_dir

    return False, agent_dir


def is_exact_python_version(version: str) -> bool:
    """Check if a version string has all three parts (major.minor.patch).

    Examples: '3.13.6' -> True, '3.13' -> False, '3' -> False.
    """
    parts = version.split(".")
    return len(parts) >= 3 and all(p.isdigit() for p in parts[:3])


def get_python_version_file() -> str | None:
    """Read the raw content of .python-version (unresolved).

    Returns the version string as written in the file, or None if
    the file doesn't exist or is empty.
    """
    pv_file = Path(".python-version")
    if pv_file.exists():
        version = pv_file.read_text().strip()
        if version:
            return version
    return None


def get_pyproject_requires_python() -> str | None:
    """Read requires-python from pyproject.toml.

    Returns the constraint string (e.g. '>=3.12', '==3.13.6') or None.
    """
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        return None

    try:
        # tomllib is stdlib in 3.11+; fall back to parsing manually
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib  # type: ignore[no-redef]
            except ImportError:
                # Manual fallback: scan for requires-python
                content = pyproject_path.read_text()
                for line in content.splitlines():
                    line = line.strip()
                    if line.startswith("requires-python"):
                        _, _, value = line.partition("=")
                        # Strip the first '=' from e.g. '= ">=3.12"'
                        value = value.lstrip("= ").strip().strip('"').strip("'")
                        if value:
                            return value
                return None

        data = tomllib.loads(pyproject_path.read_text())
        return data.get("project", {}).get("requires-python")
    except Exception:
        return None


def generate_pyproject_toml(
    project_name: str | None = None,
    python_version: str | None = None,
    dependencies: list[str] | None = None,
) -> str:
    """Generate minimal pyproject.toml content for Posit Connect deployment.

    Args:
        project_name: Project name (defaults to current directory name).
        python_version: Python version from .python-version (used for requires-python).
        dependencies: List of package specs (defaults to parsing requirements.txt).

    Returns the file content as a string.
    """
    import re

    if project_name is None:
        project_name = Path.cwd().name
    # PEP 508: lowercase, alphanumeric + hyphens
    project_name = re.sub(r"[^a-zA-Z0-9._-]", "-", project_name).lower().strip("-")

    if python_version is None:
        python_version = get_python_version_file()

    # Build requires-python from .python-version (major.minor lower bound)
    if python_version:
        parts = python_version.split(".")
        requires_python = f">={parts[0]}.{parts[1]}"
    else:
        requires_python = ">=3.12"

    if dependencies is None:
        # Parse from requirements.txt, stripping pinned versions to loose specs
        dependencies = _requirements_to_dependencies()

    # Format dependencies list
    if dependencies:
        deps_lines = "\n".join(f'    "{dep}",' for dep in dependencies)
        deps_block = f"dependencies = [\n{deps_lines}\n]"
    else:
        deps_block = "dependencies = []"

    return (
        f'[project]\nname = "{project_name}"\nversion = "0.1.0"\n'
        f'requires-python = "{requires_python}"\n{deps_block}\n'
    )


def _requirements_to_dependencies(req_path: str = "requirements.txt") -> list[str]:
    """Convert requirements.txt entries to pyproject.toml dependency specs.

    Strips exact pins (==) to minimum bounds (>=) so pyproject.toml has
    loose constraints while requirements.txt/uv.lock keep the pins.
    """
    import re

    deps = []
    for spec in get_requirements_packages(req_path):
        # Strip hashes, environment markers after ;
        spec = spec.split(";")[0].strip()
        # Convert == pins to >= (pyproject.toml should be loose)
        spec = re.sub(r"==(\d)", r">=\1", spec)
        if spec:
            deps.append(spec)
    return deps


def get_local_python_version() -> str | None:
    """Get the Python version from .python-version or the running interpreter.

    Returns the version string as-is from .python-version (e.g. '3.13' or
    '3.13.6'). Falls back to sys.version_info if no file exists.

    Does NOT resolve short versions — callers should use
    is_exact_python_version() to check and warn if needed.
    """
    pv_version = get_python_version_file()
    if pv_version:
        return pv_version

    # Fall back to running Python version
    info = sys.version_info
    return f"{info.major}.{info.minor}.{info.micro}"
