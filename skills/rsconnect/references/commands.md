# Quick Commands Reference

## R Helper Scripts

```bash
# Pre-deploy validation
Rscript $SKILL_DIR/scripts/pre_deploy_check.R

# Full diagnostics (add --verbose for renv::diagnostics() output)
Rscript $SKILL_DIR/scripts/diagnose.R
Rscript $SKILL_DIR/scripts/diagnose.R --verbose

# Fix Source:unknown (ALWAYS preview first!)
Rscript $SKILL_DIR/scripts/fix_unknown_sources.R --dry-run
Rscript $SKILL_DIR/scripts/fix_unknown_sources.R

# Regenerate manifest.json
Rscript $SKILL_DIR/scripts/regenerate_manifest.R

# Install pre-commit hook (validates deployment files before commit)
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
Rscript $SKILL_DIR/scripts/precommit_check.R
EOF
chmod +x .git/hooks/pre-commit
```

## R Commands

```r
# Update dependencies + lockfile
renv::update()
renv::snapshot()

# Regenerate manifest
rsconnect::writeManifest()

# Check status
renv::status()
renv::diagnostics()

# Fix a single package
renv::install("pkgname")
renv::install("pkgname@1.2.3")  # specific version
renv::install("bioc::pkgname")  # Bioconductor
renv::snapshot()
```

## R Common Workflows

### Deploy after code changes (R)
```bash
Rscript $SKILL_DIR/scripts/regenerate_manifest.R
git add renv.lock manifest.json
git commit -m "chore: update manifest"
git push
```

### Fix Source:unknown (recommended workflow)
```bash
# 1. Preview what will change
Rscript $SKILL_DIR/scripts/fix_unknown_sources.R --dry-run

# 2. Apply fixes (creates backup)
Rscript $SKILL_DIR/scripts/fix_unknown_sources.R

# 3. Regenerate manifest
Rscript $SKILL_DIR/scripts/regenerate_manifest.R

# 4. Verify and deploy
Rscript $SKILL_DIR/scripts/pre_deploy_check.R
git add renv.lock manifest.json && git commit -m "fix: resolve Source:unknown" && git push
```

### Rollback (R)
```bash
# Git revert
git revert HEAD && git push

# Restore from backup (after fix_unknown_sources.R)
cp renv.lock.backup.YYYYMMDD_HHMMSS renv.lock
Rscript $SKILL_DIR/scripts/regenerate_manifest.R
git add -A && git commit -m "fix: rollback" && git push
```

## R Bash One-liners

```bash
# Check for Source:unknown
grep '"Source": "unknown"' renv.lock

# Count Source:unknown packages
grep -c '"Source": "unknown"' renv.lock

# Full deploy prep
R -q -e 'renv::snapshot()' && Rscript $SKILL_DIR/scripts/regenerate_manifest.R
```

---

## Python Helper Scripts (uv)

```bash
# Pre-deploy validation (Python)
python $SKILL_DIR/scripts/pre_deploy_check_py.py

# Full diagnostics (Python)
python $SKILL_DIR/scripts/diagnose_py.py
python $SKILL_DIR/scripts/diagnose_py.py --verbose

# Regenerate manifest (auto-detect framework)
python $SKILL_DIR/scripts/regenerate_manifest_py.py

# Regenerate manifest (specify framework)
python $SKILL_DIR/scripts/regenerate_manifest_py.py --type fastapi
python $SKILL_DIR/scripts/regenerate_manifest_py.py --type api
python $SKILL_DIR/scripts/regenerate_manifest_py.py --type dash

# Skip uv export (use existing requirements.txt)
python $SKILL_DIR/scripts/regenerate_manifest_py.py --no-uv-export

# Don't patch allow_uv into manifest
python $SKILL_DIR/scripts/regenerate_manifest_py.py --no-allow-uv
```

## Python Commands (uv)

```bash
# Add/remove packages
uv add <package>
uv add "package>=1.0"
uv remove <package>

# Sync environment from lockfile
uv sync

# Generate requirements.txt for Connect
uv export --no-hashes -o requirements.txt

# Generate manifest (FastAPI)
rsconnect write-manifest fastapi .

# Generate manifest (Flask / generic API)
rsconnect write-manifest api .

# Generate manifest (Dash)
rsconnect write-manifest dash .

# Generate manifest (Streamlit)
rsconnect write-manifest streamlit .

# Generate manifest (Jupyter notebook)
rsconnect write-manifest notebook .

# Install rsconnect-python as a tool
uv tool install rsconnect-python

# Use rsconnect-python without installing
uvx rsconnect-python write-manifest fastapi .
```

## Python Common Workflows

### Deploy after code changes (Python)
```bash
uv export --no-hashes -o requirements.txt
python $SKILL_DIR/scripts/regenerate_manifest_py.py
git add requirements.txt manifest.json
git commit -m "chore: update manifest"
git push
```

### Full deploy prep (Python)
```bash
uv export --no-hashes -o requirements.txt && python $SKILL_DIR/scripts/regenerate_manifest_py.py
python $SKILL_DIR/scripts/pre_deploy_check_py.py
git add requirements.txt manifest.json && git commit -m "chore: update manifest" && git push
```

### Python version upgrade
```bash
# Update .python-version, then:
uv sync
uv export --no-hashes -o requirements.txt
python $SKILL_DIR/scripts/regenerate_manifest_py.py
git add .python-version requirements.txt manifest.json
git commit -m "chore: upgrade Python version"
git push
```

### Rollback (Python)
```bash
# Git revert
git revert HEAD && git push
```

## Python Bash One-liners

```bash
# Check Python version in manifest
python -c "import json; print(json.load(open('manifest.json')).get('python', {}).get('version', 'not set'))"

# Check allow_uv status
python -c "import json; m=json.load(open('manifest.json')); print(m.get('python',{}).get('package_manager',{}).get('allow_uv', 'not set'))"

# Count packages in requirements.txt
grep -cv '^\s*$\|^\s*#\|^-' requirements.txt
```
