# Troubleshooting Posit Connect Deployments

## Diagnosing issues

```r
# Full renv diagnostics (cache, repos, settings)
renv::diagnostics()

# Check lockfile vs library sync
renv::status()

# Validate lockfile structure
renv::lockfile_validate()
```

Or use the helper script:
```bash
Rscript .claude/skills/rsconnect/scripts/diagnose.R --verbose
```

---

## `Source: unknown` in renv.lock

This is the **most common deployment blocker**. Connect can't restore packages without a known source.

**Error messages:**
- `Unable to determine package source for [source] package`
- `renv may be unable to restore these packages in the future`

**Causes & fixes:**

| Cause | Fix |
| --- | --- |
| Installed via `install.packages()` from local file | Reinstall from CRAN: `renv::install("pkg")` |
| Internal repo not in `options("repos")` | Add repo URL to `.Rprofile` before `renv::install()` |
| Package from Posit Package Manager | Ensure RSPM URL is in `options("repos")` before snapshot |
| Bioconductor package | Use `renv::install("bioc::pkgname")` syntax |
| Package moved from BioConductor to CRAN (or vice versa) | Reinstall from current location |

**Automated fix:**
```bash
Rscript .claude/skills/rsconnect/scripts/fix_unknown_sources.R --dry-run
```

**Verify fix worked:**
```bash
grep '"Source": "unknown"' renv.lock  # Should return nothing
```

---

## Common restore/build errors

### `Failed to retrieve package sources for X from CRAN`
**Cause:** Package archived on CRAN, version not available, or repo mismatch.
**Fix:**
```r
# Use Posit Package Manager with time-machine snapshots
options(repos = c(CRAN = "https://packagemanager.posit.co/cran/2025-01-15"))
renv::install("pkgname")
renv::snapshot()
```

### `r-package-not-available`
**Cause:** Dependency missing from `manifest.json` or unavailable version.
**Fix:** Ensure the package is explicitly used/imported, update packages if needed, then rerun `rsconnect::writeManifest()`.

### `A required R package was found but the specified version is not available`
**Cause:** Version mismatch between your lockfile and what's available in Connect's repos.
**Fix:** Either update to an available version or configure RSPM time-machine snapshot.

### `Can't re-install packages installed from source`
**Cause:** `renv.lock` references a local/source-only install (`Source: unknown`).
**Fix:** Reinstall from CRAN so `Source` is resolvable, then `renv::snapshot()`.

### `package 'X' is not available for R version ...`
**Cause:** R version in manifest doesn't match the target runtime or package repo.
**Fix:** Regenerate the manifest from the correct R version or update the Connect image.

---

## Bundle/file limit errors

### `Bundle has too many files` / `bundle size exceeds limit`

**Default limits (rsconnect 1.6.0+):**
- `rsconnect.max.bundle.files` = 10,000 files
- `rsconnect.max.bundle.size` = 5 GiB

**Fixes:**
1. Add non-app files to `.rscignore`
2. Deploy from a clean subdirectory
3. Use `appFiles` parameter to explicitly list files
4. Increase limits if needed:
   ```r
   options(rsconnect.max.bundle.files = 15000)
   rsconnect::writeManifest()
   ```

---

## Manifest/lockfile issues

### App runs locally but fails on Connect with missing package
**Cause:** Manifest is stale or package not detected via `::` usage.
**Fix:** Add explicit `library()` call or DESCRIPTION Imports, then regenerate manifest.

### Manifest out of sync with renv.lock
**Cause:** Updated packages but didn't regenerate manifest.
**Fix:**
```bash
Rscript .claude/skills/rsconnect/scripts/regenerate_manifest.R
```

---

## R version migration issues

### Connect uses different R version than expected
**Cause:** Connect finds closest available R version if exact match unavailable.
**Check:** Look in deployment logs for "requested R version X but using Y"
**Fix:** Either install matching R version on Connect or regenerate manifest from available version.

### Packages fail to install after R upgrade
**Cause:** Binary packages compiled for old R version.
**Fix:**
```r
# Reinstall all packages for new R version
renv::rebuild()
renv::snapshot()
```

---

## Repository configuration issues

### `unable to access index for repository`
**Cause:** Connect server can't reach the package repository URL.
**Check:** Ask admin to verify Connect's `repos` configuration.

### Different repos on dev machine vs Connect
**Cause:** Your `options("repos")` differs from Connect's server-side config.
**Fix:** Ensure repo URLs in `.Rprofile` match what Connect can access, or use RSPM.

---

## Log interpretation

| Log message | Meaning | Action |
| --- | --- | --- |
| `Locale` warnings | Informational | Ignore unless encoding issues |
| `Loading R/ directory...` | Informational | None |
| `Listening on http://127.0.0.1:PORT` | App started successfully | None |
| `r-package-not-available` | Missing/unavailable dependency | Update packages + regenerate manifest |
| `curl: (22) ... 404` | Package version not in repo | Use RSPM snapshot |
| `unable to access index for repository` | Repo URL unreachable | Check Connect repo config |
| `requested R version X but using Y` | R version mismatch | Install matching R or regenerate |

---

## Where to find logs

1. **Connect UI:** Content -> Your App -> Logs tab
2. **Deployment logs:** Shows during publish, or in Connect UI -> Info -> Deployments
3. **Runtime logs:** Connect UI -> Logs (shows app stdout/stderr)

## Getting help

Before opening a support ticket, run:
```bash
Rscript .claude/skills/rsconnect/scripts/diagnose.R --verbose > diagnostics.txt 2>&1
```

This captures environment info, package versions, and renv status useful for debugging.
