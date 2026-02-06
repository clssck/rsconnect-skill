# rsconnect-skill

Agent skill for Posit Connect and rsconnect deployment workflows.

Handles Git-backed deployment, manifest management, renv lockfile issues,
Source:unknown errors, R version upgrades, and pre-commit validation.

## Install

```bash
# Via skills CLI (recommended)
npx skills add <owner>/rsconnect-skill

# Install to a specific agent
npx skills add <owner>/rsconnect-skill -a claude-code

# List available skills before installing
npx skills add <owner>/rsconnect-skill --list
```

### Manual Installation

```bash
# Copy the skill directory into your project
cp -r skills/rsconnect/ /path/to/your-project/.claude/skills/rsconnect/
```

After installation, your project should have:

```
your-project/
  .claude/
    skills/
      rsconnect/
        SKILL.md
        scripts/
        references/
```

## What's Included

### Skill (SKILL.md)

Provides the agent with:
- Dynamic project status (R version, rsconnect version, Source:unknown count)
- Deployment method guidance (Git-backed, IDE, CLI, Jupyter, command line)
- Common workflow recipes (deploy, fix errors, rollback, R upgrade)
- Branch strategy recommendations (deploy branch, multi-environment)

### Helper Scripts

| Script | Purpose | Flags |
|--------|---------|-------|
| `pre_deploy_check.R` | Validate deployment readiness (5 checks) | |
| `diagnose.R` | Full diagnostics report | `--verbose`, `--help` |
| `fix_unknown_sources.R` | Fix Source:unknown packages safely | `--dry-run`, `--help` |
| `regenerate_manifest.R` | Regenerate manifest.json | |
| `precommit_check.R` | Git pre-commit hook validation | |

Scripts share a common utility library (`scripts/lib/parse_utils.R`) for consistent output formatting and renv.lock parsing.

```bash
# Run from project root
Rscript .claude/skills/rsconnect/scripts/<script>.R
```

### Pre-commit Hook

Validates deployment files before each commit:

```bash
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
Rscript .claude/skills/rsconnect/scripts/precommit_check.R
EOF
chmod +x .git/hooks/pre-commit
```

### References

| File | Content |
|------|---------|
| `references/commands.md` | Quick command reference |
| `references/troubleshooting.md` | Common errors, rsconnect 1.6.0+ changes, bundle limits, R migrations |

## Requirements

- R (any recent version)
- `renv` package
- `rsconnect` package (>= 0.8.15 for Git-backed deployment)

## Trigger Keywords

The skill activates when the agent detects these topics:
deploy, publish, Connect, rsconnect, manifest.json, renv.lock,
Source unknown, package restore, bundle error, writeManifest,
R version upgrade, git-backed content

## Compatibility

| Feature | Claude Code | Other Agents |
|---------|-------------|--------------|
| Basic skill (SKILL.md) | Yes | Yes |
| Dynamic context (`!` commands) | Yes | Agent-dependent |
| `argument-hint` | Yes | Agent-dependent |
| Helper scripts (R) | Yes (requires R) | Yes (requires R) |

## License

MIT
