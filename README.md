# rsconnect-skill

Claude Code skill for Posit Connect and rsconnect deployment workflows.

Handles Git-backed deployment, manifest management, renv lockfile issues,
Source:unknown errors, R version upgrades, and pre-commit validation.

## Installation

Clone or copy the `rsconnect/` folder into your project's `.claude/skills/` directory:

```bash
# Option 1: Copy directly
cp -r rsconnect/ /path/to/your-project/.claude/skills/rsconnect/

# Option 2: Clone and copy
git clone <this-repo-url> /tmp/rsconnect-skill
cp -r /tmp/rsconnect-skill/rsconnect/ /path/to/your-project/.claude/skills/rsconnect/
```

After installation, your project structure should look like:

```
your-project/
  .claude/
    skills/
      rsconnect/
        SKILL.md
        scripts/
          pre_deploy_check.R
          diagnose.R
          fix_unknown_sources.R
          regenerate_manifest.R
          precommit_check.R
          lib/
            parse_utils.R
          README.md
        references/
          commands.md
          troubleshooting.md
```

## What's Included

### SKILL.md
Main skill entry point. Provides Claude with:
- Dynamic project status (R version, rsconnect version, Source:unknown count)
- Deployment method guidance (Git-backed, IDE, CLI, etc.)
- Common workflow recipes
- Branch strategy recommendations

### Helper Scripts

| Script | Purpose | Flags |
|--------|---------|-------|
| `pre_deploy_check.R` | Validate deployment readiness (5 checks) | |
| `diagnose.R` | Full diagnostics report | `--verbose`, `--help` |
| `fix_unknown_sources.R` | Fix Source:unknown packages safely | `--dry-run`, `--help` |
| `regenerate_manifest.R` | Regenerate manifest.json | |
| `precommit_check.R` | Git pre-commit hook validation | |

All scripts are run from the project root:

```bash
Rscript .claude/skills/rsconnect/scripts/<script>.R
```

### Pre-commit Hook

Install the Git pre-commit hook to validate deployment files before each commit:

```bash
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
Rscript .claude/skills/rsconnect/scripts/precommit_check.R
EOF
chmod +x .git/hooks/pre-commit
```

### References

- `references/commands.md` - Quick command reference
- `references/troubleshooting.md` - Common errors and fixes (rsconnect 1.6.0+, bundle limits, R migrations)

## Requirements

- R (any recent version)
- `renv` package
- `rsconnect` package (>= 0.8.15 for Git-backed deployment)

## Trigger Keywords

The skill activates when Claude detects these topics:
deploy, publish, Connect, rsconnect, manifest.json, renv.lock,
Source unknown, package restore, bundle error, writeManifest,
R version upgrade, git-backed content
