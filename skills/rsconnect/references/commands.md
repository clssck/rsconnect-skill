# Quick Commands Reference

## Helper Scripts

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

## Common Workflows

### Deploy after code changes
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

### Rollback
```bash
# Git revert
git revert HEAD && git push

# Restore from backup (after fix_unknown_sources.R)
cp renv.lock.backup.YYYYMMDD_HHMMSS renv.lock
Rscript $SKILL_DIR/scripts/regenerate_manifest.R
git add -A && git commit -m "fix: rollback" && git push
```

## Bash One-liners

```bash
# Check for Source:unknown
grep '"Source": "unknown"' renv.lock

# Count Source:unknown packages
grep -c '"Source": "unknown"' renv.lock

# Full deploy prep
R -q -e 'renv::snapshot()' && Rscript $SKILL_DIR/scripts/regenerate_manifest.R
```
