# rsconnect Helper Scripts

Run all scripts from the project root directory.

## Quick Reference

| Script | Purpose | Exit Codes |
|--------|---------|------------|
| `pre_deploy_check.R` | Validate deployment readiness | 0=ready, 1=issues |
| `diagnose.R` | Full diagnostics report | 0=healthy, 1=issues |
| `fix_unknown_sources.R` | Fix Source:unknown packages | 0=fixed, 1=failed |
| `regenerate_manifest.R` | Regenerate manifest.json | 0=success, 1=failed |
| `precommit_check.R` | Git pre-commit hook | 0=OK, 1=block commit |

---

## pre_deploy_check.R

**Purpose:** Quick validation before deploying to Posit Connect.

**Checks:**
1. `manifest.json` exists
2. rsconnect package version ≥ 0.8.15
3. No packages with `Source: unknown` in renv.lock
4. manifest.json is newer than renv.lock (sync check)
5. Local library sync status (informational, doesn't block)

**Usage:**
```bash
Rscript $SKILL_DIR/scripts/pre_deploy_check.R
```

**Note:** renv may print status messages before the check runs (from `.Rprofile` activation). Look for the boxed "PRE-DEPLOY CHECK" header for the actual results.

**Exit codes:**
- `0` — Ready to deploy
- `1` — Issues found (see output for fixes)

---

## diagnose.R

**Purpose:** Comprehensive diagnostics for troubleshooting deployment issues.

**Reports:**
- R and package versions (renv, rsconnect)
- Key file status (renv.lock, manifest.json, .Rprofile, .rscignore)
- renv sync status
- Source:unknown package scan
- Repository configuration
- Full `renv::diagnostics()` output (with `--verbose`)

**Usage:**
```bash
# Standard diagnostics
Rscript $SKILL_DIR/scripts/diagnose.R

# Include full renv::diagnostics() output
Rscript $SKILL_DIR/scripts/diagnose.R --verbose

# Show help
Rscript $SKILL_DIR/scripts/diagnose.R --help
```

**Flags:**
- `--verbose`, `-v` — Include full renv::diagnostics() output
- `--help`, `-h` — Show help message

**Exit codes:**
- `0` — No issues detected
- `1` — Issues found

**When to use:**
- Deployment fails on Connect
- Package restore errors
- "Can't find package" errors
- Before opening a support ticket (captures useful info)

---

## fix_unknown_sources.R

**Purpose:** Automatically fix packages with `Source: unknown` in renv.lock.

**Safety features:**
- `--dry-run` mode shows what would change without modifying files
- Creates timestamped backup of renv.lock before any changes
- Preserves package versions from renv.lock when reinstalling

**What it does:**
1. Scans renv.lock for `Source: unknown` entries
2. Identifies the package names and versions
3. Creates backup: `renv.lock.backup.YYYYMMDD_HHMMSS`
4. Reinstalls each package from CRAN (preserving version)
5. Runs `renv::snapshot()` to update lockfile
6. Verifies the fix worked

**Usage:**
```bash
# Preview changes (RECOMMENDED first step)
Rscript $SKILL_DIR/scripts/fix_unknown_sources.R --dry-run

# Apply fixes (creates backup automatically)
Rscript $SKILL_DIR/scripts/fix_unknown_sources.R

# Show help
Rscript $SKILL_DIR/scripts/fix_unknown_sources.R --help
```

**Flags:**
- `--dry-run`, `-n` — Show what would be done without making changes
- `--help`, `-h` — Show help message

**Exit codes:**
- `0` — All issues fixed (or none found)
- `1` — Some packages couldn't be fixed automatically

**Manual fallback:** If automatic fix fails:
```r
# Try specific version from Posit Package Manager
options(repos = c(CRAN = "https://packagemanager.posit.co/cran/latest"))
renv::install("pkgname@1.2.3")
renv::snapshot()
```

**To restore from backup:**
```bash
cp renv.lock.backup.YYYYMMDD_HHMMSS renv.lock
```

---

## regenerate_manifest.R

**Purpose:** Regenerate `manifest.json` for Git-backed deployment.

**What it does:**
1. Sets bundle file limit to 5000 (handles large apps)
2. Runs `rsconnect::writeManifest()`
3. Verifies manifest was created
4. Reports success or failure with next steps

**Usage:**
```bash
Rscript $SKILL_DIR/scripts/regenerate_manifest.R
```

**Exit codes:**
- `0` — Manifest regenerated successfully
- `1` — Failed (rsconnect not installed or writeManifest error)

---

## precommit_check.R

**Purpose:** Git pre-commit hook that validates deployment files before allowing a commit.

**Checks (only when relevant files are staged):**
1. No `Source: unknown` packages in renv.lock (blocks commit)
2. manifest.json freshness when renv.lock is staged (warning only)
3. manifest.json exists when renv.lock is staged (blocks commit)

**Installation:**
```bash
# Create pre-commit hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
Rscript $SKILL_DIR/scripts/precommit_check.R
EOF
chmod +x .git/hooks/pre-commit
```

**Usage:**
The hook runs automatically on `git commit` when renv.lock or manifest.json are staged.

```bash
# Manual test run
Rscript $SKILL_DIR/scripts/precommit_check.R

# Bypass hook (not recommended)
git commit --no-verify
```

**Exit codes:**
- `0` — OK to commit (no issues or no deployment files staged)
- `1` — Commit blocked (critical issues found)

**Note:** The hook only runs checks when `renv.lock` or `manifest.json` are staged for commit. Regular code changes won't trigger the validation.

---

## Shared Utilities (lib/parse_utils.R)

The scripts share common utilities in `lib/parse_utils.R`:

- `parse_unknown_sources()` — Find packages with Source:unknown
- `get_package_version()` — Get version from renv.lock
- `box_header()` / `box_result()` — Consistent output formatting
- `SYM_CHECK`, `SYM_CROSS`, `SYM_WARN` — Unicode symbols

---

## Typical Workflow

```bash
# 1. Check current status
Rscript $SKILL_DIR/scripts/pre_deploy_check.R

# 2. If Source:unknown issues, preview fixes first
Rscript $SKILL_DIR/scripts/fix_unknown_sources.R --dry-run

# 3. Apply fixes (creates backup)
Rscript $SKILL_DIR/scripts/fix_unknown_sources.R

# 4. Regenerate manifest
Rscript $SKILL_DIR/scripts/regenerate_manifest.R

# 5. Verify ready
Rscript $SKILL_DIR/scripts/pre_deploy_check.R

# 6. Commit and push
git add renv.lock manifest.json
git commit -m "chore: update manifest for deploy"
git push
```

## Troubleshooting Scripts

**Script fails to find lib/parse_utils.R:**
- Make sure you're running from the project root
- The scripts auto-detect their location; if that fails, they fall back to current directory

**renv messages appear before script output:**
- This is normal; renv auto-activates from .Rprofile
- Look for the boxed header (e.g., "PRE-DEPLOY CHECK") for actual results

**Script can't find packages:**
- Ensure renv is activated (check .Rprofile exists)
- Run `renv::restore()` to sync local library
