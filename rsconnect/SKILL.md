---
name: rsconnect
description: Posit Connect and rsconnect deployment workflows. Use for deploying/publishing to Connect, deployment errors, git-backed content, R version upgrades, regenerating manifest.json, fixing renv/renv.lock issues, resolving Source unknown errors, package restore failures, bundle errors, writeManifest problems.
argument-hint: "[error-message] or [package-name]"
---

# Posit Connect Deployment Guide

## Quick Start (First-Time Deploy)

```bash
# 1. Check if ready to deploy
Rscript .claude/skills/rsconnect/scripts/pre_deploy_check.R

# 2. Fix any issues reported, then commit
git add manifest.json renv.lock && git commit -m "chore: update manifest"

# 3. Push (Connect auto-deploys from Git)
git push
```

## Current Project Status

**R Version:** !`R --version 2>/dev/null | head -1 || echo 'R not detected'`
**rsconnect:** !`R -q -e 'cat(as.character(packageVersion("rsconnect")))' 2>/dev/null || echo 'Not installed'`
**renv:** !`R -q -e 'cat(as.character(packageVersion("renv")))' 2>/dev/null || echo 'Not installed'`
**Manifest:** !`test -f manifest.json && echo 'Present' || echo 'MISSING'`
**Source Unknown:** !`grep -c '"Source": "unknown"' renv.lock 2>/dev/null | cat` packages
**Status:** !`test -f manifest.json && ! grep -q '"Source": "unknown"' renv.lock 2>/dev/null && echo 'Ready to deploy' || echo 'Check issues above'`

**User request:** $ARGUMENTS

---

## Before Proceeding

**Ask the user if not clear from context:**

1. **How is this app deployed to Connect?**
   - **Git-backed** — Connect pulls from Git automatically (needs `manifest.json`) - *simplest for teams*
   - **RStudio IDE** — Click "Publish" button in IDE
   - **R console** — `rsconnect::deployApp()`
   - **Jupyter** — Publish from notebook interface
   - **Command line** — `rsconnect deploy manifest`
   - **Not sure** — Check Connect UI → Content → Your App → Info tab (shows deployment source)

2. **If Git-backed, what branch does Connect watch?**
   - Check Connect UI → Content → Your App → Info → "Git Repository" section
   - **Recommendation:** Use a dedicated deploy branch (e.g., `deploy`, `production`) so you control when changes go live

> Note: **This skill focuses on Git-backed deployment** (the default for this project). For push-button methods, the main difference is you don't need `manifest.json` — rsconnect generates the bundle on-the-fly.

---

## Key Concepts

### renv.lock vs manifest.json

| File | Purpose | When to Update |
|------|---------|----------------|
| `renv.lock` | Records YOUR local package versions | After `renv::install()` or `renv::update()` |
| `manifest.json` | Tells Connect what to install | After changing `renv.lock` or app files |

**They can drift!** Always update both together:
```r
renv::snapshot()           # Update renv.lock
rsconnect::writeManifest() # Update manifest.json
```

### What is "Source: unknown"?

Connect needs to know WHERE to download each package. `Source: unknown` means Connect can't find it.

**Common causes:** Package installed from local file, missing repo in options, Bioconductor package without prefix.

**Fix:** `Rscript .claude/skills/rsconnect/scripts/fix_unknown_sources.R --dry-run`

---

## Helper Scripts

| Script | Purpose | Flags |
|--------|---------|-------|
| `pre_deploy_check.R` | Validate deployment readiness | |
| `diagnose.R` | Full diagnostics report | `--verbose` |
| `fix_unknown_sources.R` | Fix Source:unknown packages | `--dry-run`, `--help` |
| `regenerate_manifest.R` | Regenerate manifest.json | |
| `precommit_check.R` | Git pre-commit hook validation | |

```bash
# Run from project root
Rscript .claude/skills/rsconnect/scripts/<script>.R
```

### Git Pre-commit Hook

Automatically validate deployment files before each commit:

```bash
# Install the pre-commit hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
Rscript .claude/skills/rsconnect/scripts/precommit_check.R
EOF
chmod +x .git/hooks/pre-commit
```

The hook checks:
- No `Source: unknown` packages in staged `renv.lock`
- Manifest freshness when `renv.lock` is staged
- Manifest exists when `renv.lock` is staged

To bypass (not recommended): `git commit --no-verify`

---

## Common Workflows

### Deploy After Code Changes

```bash
renv::snapshot()  # If dependencies changed
Rscript .claude/skills/rsconnect/scripts/regenerate_manifest.R
git add renv.lock manifest.json
git commit -m "chore: update manifest"
git push
```

### Fix Source:unknown Error

```bash
# 1. See what would change (safe)
Rscript .claude/skills/rsconnect/scripts/fix_unknown_sources.R --dry-run

# 2. Apply fixes (creates backup)
Rscript .claude/skills/rsconnect/scripts/fix_unknown_sources.R

# 3. Regenerate manifest
Rscript .claude/skills/rsconnect/scripts/regenerate_manifest.R
```

### Rollback a Bad Deployment

```bash
# Option 1: Revert to previous commit
git revert HEAD
git push

# Option 2: Restore from backup (if fix_unknown_sources.R was run)
cp renv.lock.backup.YYYYMMDD_HHMMSS renv.lock
Rscript .claude/skills/rsconnect/scripts/regenerate_manifest.R
git add -A && git commit -m "fix: rollback deployment"
git push

# Option 3: In Connect UI
# Go to Content → Your App → History → Activate previous bundle
```

### R Version Upgrade

1. Install new R version
2. Back up: `cp renv.lock renv.lock.bak`
3. From new R session:
   ```r
   renv::init()  # Select option 2: re-initialize
   ```
4. Fix any Source:unknown issues
5. Regenerate manifest and deploy

See [references/troubleshooting.md](references/troubleshooting.md) for detailed migration steps.

---

## Deployment Methods

| Method | Best For | Needs manifest.json? |
|--------|----------|---------------------|
| **Git-backed** | Teams, CI/CD, reproducibility | Yes |
| RStudio IDE | Quick one-off deploys | No (auto-generated) |
| R console | Scripted deploys | No |
| Jupyter | Python/R notebooks | No |
| CLI (`rsconnect deploy`) | CI pipelines without Git integration | Yes |

### Git-backed (This Project)

**How it works:**
1. You generate `manifest.json` locally
2. You push to Git (with manifest.json and renv.lock)
3. Connect polls your branch (configurable, default 15 min) and auto-deploys

**Why it's the easiest for teams:**
- No credentials needed on dev machines (just Git access)
- Deployment = `git push`
- Full audit trail in Git history
- Easy rollback (`git revert`)

**Requirements:** rsconnect ≥ 0.8.15, manifest.json committed to repo

> **Note:** Once Git-backed, stay Git-backed. You can't switch to push-button without recreating the content in Connect.

---

## Branch Strategy

### Recommended: Deploy Branch

```
main (development)
  │
  └── deploy (Connect watches this branch)
```

**Workflow:**
```bash
# Develop on main
git checkout main
# ... make changes ...
git commit -m "feat: new feature"

# When ready to deploy, merge to deploy branch
git checkout deploy
git merge main
Rscript .claude/skills/rsconnect/scripts/regenerate_manifest.R
git add manifest.json renv.lock
git commit -m "chore: update manifest for deploy"
git push origin deploy
```

### Multi-environment Setup

```
main (development)
  ├── staging (Connect staging server watches)
  └── production (Connect prod server watches)
```

Each Connect server points to a different branch. Merge up through environments:
`main` → `staging` → `production`

---

## Pre-deploy Checklist

- [ ] Run `Rscript .claude/skills/rsconnect/scripts/pre_deploy_check.R`
- [ ] No Source:unknown packages
- [ ] Manifest is up to date
- [ ] `.rscignore` excludes dev artifacts
- [ ] On correct branch for deployment
- [ ] Commit and push

---

## Additional Resources

- **Script docs:** [scripts/README.md](scripts/README.md)
- **Troubleshooting:** [references/troubleshooting.md](references/troubleshooting.md)
- **Commands:** [references/commands.md](references/commands.md)
- **Manifest guide:** [../../../docs/manifest-update-guide.md](../../../docs/manifest-update-guide.md)

### External Links

- [Posit Connect Git-backed docs](https://docs.posit.co/connect/user/git-backed/)
- [renv documentation](https://rstudio.github.io/renv/)
- [rsconnect writeManifest](https://rstudio.github.io/rsconnect/reference/writeManifest.html)
