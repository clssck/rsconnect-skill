# rsconnect-skill

Agent skill for Posit Connect and rsconnect deployment workflows.

Handles Git-backed deployment, manifest management, renv lockfile issues,
Source:unknown errors, R version upgrades, and pre-commit validation.

## Supported Agents

| Agent | Install Method | Status |
|-------|---------------|--------|
| [Cursor](https://cursor.com) | `npx skills add` | Fully supported |
| [Claude Code](https://claude.ai) | `npx skills add` | Fully supported |
| [Codex](https://openai.com/codex) | `npx skills add` | Fully supported |
| [Copilot](https://github.com/features/copilot) | Manual install | Fully supported |
| Any agent supporting [agentskills.io](https://agentskills.io) | `npx skills add` | Fully supported |

## Install

```bash
# Via skills CLI (recommended — auto-detects your agent)
npx skills add <owner>/rsconnect-skill

# Install to a specific agent
npx skills add <owner>/rsconnect-skill -a cursor
npx skills add <owner>/rsconnect-skill -a claude-code
npx skills add <owner>/rsconnect-skill -a codex
```

### Manual Installation

Copy the skill into your agent's skills directory:

```bash
# Cursor
cp -r skills/rsconnect/ /path/to/your-project/.cursor/skills/rsconnect/

# Claude Code
cp -r skills/rsconnect/ /path/to/your-project/.claude/skills/rsconnect/

# Copilot (or any agent using .github/)
cp -r skills/rsconnect/ /path/to/your-project/.github/skills/rsconnect/

# Generic — adapt the path to your agent's convention
cp -r skills/rsconnect/ /path/to/your-project/<agent-skills-dir>/rsconnect/
```

After installation, your project should have:

```
your-project/
  <agent-skills-dir>/
    rsconnect/
      SKILL.md
      scripts/
      references/
```

Where `<agent-skills-dir>` is your agent's skills directory (e.g., `.cursor/skills/`, `.claude/skills/`, `.github/skills/`, etc.).

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

Scripts share a common utility library (`scripts/lib/parse_utils.R`) for consistent output formatting and renv.lock parsing. Scripts auto-detect their install location at runtime — no hardcoded paths.

```bash
# Run from project root (replace $SKILL_DIR with your actual skill path)
Rscript $SKILL_DIR/scripts/<script>.R
```

### Pre-commit Hook

Validates deployment files before each commit:

```bash
# Replace $SKILL_DIR with your actual skill path
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
Rscript $SKILL_DIR/scripts/precommit_check.R
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

| Feature | Support |
|---------|---------|
| Basic skill (SKILL.md) | All agents |
| Helper scripts (R) | All agents (requires R) |
| Path resolution | Agent-agnostic (`$SKILL_DIR` convention) |
| Pre-commit hook | Any Git workflow |

## License

MIT
