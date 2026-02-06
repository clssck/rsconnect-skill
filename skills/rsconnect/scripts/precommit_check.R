#!/usr/bin/env Rscript
# Pre-commit hook for rsconnect deployments
# Validates renv.lock and manifest.json before commit
# Exit 0 = OK to commit, Exit 1 = block commit

# Source shared utilities
script_dir <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1]))
if (length(script_dir) == 0 || is.na(script_dir)) script_dir <- "."
utils_path <- file.path(script_dir, "lib", "parse_utils.R")
if (file.exists(utils_path)) {
  source(utils_path)
} else {
  # Fallback if lib not found
  SYM_CHECK <- "[OK]"
  SYM_CROSS <- "[FAIL]"
  SYM_WARN <- "[WARN]"
  parse_unknown_sources <- function(path) {
    if (!file.exists(path)) return(character())
    content <- readLines(path, warn = FALSE)
    lines <- grep('"Source":\\s*"unknown"', content)
    if (length(lines) == 0) return(character())
    # Simple extraction
    pkgs <- character()
    for (ln in lines) {
      for (i in seq(ln, max(1, ln - 10), by = -1)) {
        if (grepl('"Package":', content[i])) {
          pkgs <- c(pkgs, sub('.*"Package":\\s*"([^"]+)".*', "\\1", content[i]))
          break
        }
      }
    }
    unique(pkgs)
  }
}

# Check what's staged for commit
staged_files <- tryCatch({
  system("git diff --cached --name-only", intern = TRUE)
}, error = function(e) character())

# Only run checks if relevant files are staged
renv_staged <- "renv.lock" %in% staged_files
manifest_staged <- "manifest.json" %in% staged_files

if (!renv_staged && !manifest_staged) {
  # No deployment files staged, nothing to check
  quit(status = 0)
}

cat("\n[rsconnect] Pre-commit check\n")
cat("----------------------------\n")

issues <- character()

# Check 1: Source:unknown in renv.lock
if (renv_staged && file.exists("renv.lock")) {
  cat("Checking renv.lock for Source:unknown... ")
  unknown_pkgs <- parse_unknown_sources("renv.lock")
  if (length(unknown_pkgs) > 0) {
    cat(SYM_CROSS, "\n")
    cat("  Packages with Source:unknown:", paste(unknown_pkgs, collapse = ", "), "\n")
    cat("  Fix: Rscript", skill_script_path("fix_unknown_sources.R", script_dir), "\n")
    issues <- c(issues, "Source:unknown packages found")
  } else {
    cat(SYM_CHECK, "\n")
  }
}

# Check 2: Manifest freshness (if both files exist)
if (file.exists("manifest.json") && file.exists("renv.lock")) {
  cat("Checking manifest freshness... ")
  manifest_time <- file.mtime("manifest.json")
  lock_time <- file.mtime("renv.lock")

  if (!is.na(manifest_time) && !is.na(lock_time)) {
    if (renv_staged && !manifest_staged && lock_time > manifest_time) {
      cat(SYM_WARN, "\n")
      cat("  renv.lock is staged but manifest.json is not updated\n")
      cat("  Consider: Rscript", skill_script_path("regenerate_manifest.R", script_dir), "\n")
      # Warning only, don't block
    } else if (manifest_time < lock_time) {
      cat(SYM_WARN, " manifest may be stale\n")
    } else {
      cat(SYM_CHECK, "\n")
    }
  } else {
    cat("? couldn't check file times\n")
  }
}

# Check 3: Manifest exists if renv.lock is staged
if (renv_staged && !file.exists("manifest.json")) {
  cat("Checking manifest exists... ", SYM_CROSS, "\n")
  cat("  manifest.json missing - deployment will fail\n")
  cat("  Fix: Rscript", skill_script_path("regenerate_manifest.R", script_dir), "\n")
  issues <- c(issues, "manifest.json missing")
}

cat("----------------------------\n")

if (length(issues) > 0) {
  cat(SYM_CROSS, " Commit blocked:", length(issues), "issue(s)\n")
  cat("\nTo bypass this check (not recommended):\n")
  cat("  git commit --no-verify\n\n")
  quit(status = 1)
} else {
  cat(SYM_CHECK, " Ready to commit\n\n")
  quit(status = 0)
}
