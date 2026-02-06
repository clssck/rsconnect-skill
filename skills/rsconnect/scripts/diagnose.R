#!/usr/bin/env Rscript
# Diagnose renv and rsconnect deployment issues
# Runs status checks and summarizes problems found

# Parse command line arguments
args <- commandArgs(trailingOnly = TRUE)
verbose <- "--verbose" %in% args || "-v" %in% args
help_requested <- "--help" %in% args || "-h" %in% args

if (help_requested) {
  cat("Usage: Rscript diagnose.R [OPTIONS]\n\n")
  cat("Options:\n")
  cat("  --verbose, -v  Include full renv::diagnostics() output\n")
  cat("  --help, -h     Show this help message\n")
  cat("\nThis script checks:\n")
  cat("  - Environment info (R, renv, rsconnect versions)\n")
  cat("  - Key files (renv.lock, manifest.json, etc.)\n")
  cat("  - renv sync status\n")
  cat("  - Source:unknown packages\n")
  cat("  - Repository configuration\n")
  quit(status = 0)
}

# Source shared utilities
script_dir <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1]))
if (length(script_dir) == 0 || is.na(script_dir)) script_dir <- "."
source(file.path(script_dir, "lib", "parse_utils.R"))

issues <- character()

box_header("DEPLOYMENT DIAGNOSTICS")

# Section 1: Environment info
cat("--- Environment ---\n")
cat("R version:", R.version.string, "\n")
cat("Working dir:", getwd(), "\n")

if (requireNamespace("renv", quietly = TRUE)) {
  cat("renv version:", as.character(packageVersion("renv")), "\n")
} else {
  cat("renv: NOT INSTALLED\n")
  issues <- c(issues, "renv not installed - run: install.packages('renv')")
}

if (requireNamespace("rsconnect", quietly = TRUE)) {
  rsconnect_ver <- packageVersion("rsconnect")
  cat("rsconnect version:", as.character(rsconnect_ver), "\n")
  # rsconnect 0.8.15 is minimum for Git-backed deployment
  if (rsconnect_ver < package_version("0.8.15")) {
    issues <- c(issues, "rsconnect version too old - run: install.packages('rsconnect')")
  }
} else {
  cat("rsconnect: NOT INSTALLED\n")
  issues <- c(issues, "rsconnect not installed - run: install.packages('rsconnect')")
}
cat("\n")

# Section 2: Key files
cat("--- Key Files ---\n")
files <- c("renv.lock", "manifest.json", ".Rprofile", "renv/activate.R", ".rscignore")
for (f in files) {
  if (file.exists(f)) {
    mtime <- format(file.mtime(f), "%Y-%m-%d %H:%M")
    cat(SYM_CHECK, f, "(", mtime, ")\n")
  } else {
    cat(SYM_CROSS, f, "- missing\n")
    if (f == "manifest.json") {
      issues <- c(issues, "manifest.json missing - run: rsconnect::writeManifest()")
    }
  }
}
cat("\n")

# Section 3: renv status
cat("--- renv Status ---\n")
if (requireNamespace("renv", quietly = TRUE)) {
  tryCatch({
    # Suppress verbose output
    invisible(capture.output({
      status <- renv::status()
    }, type = "output"))

    if (isTRUE(status) || (is.list(status) && length(status$library$Packages) == 0)) {
      cat(SYM_CHECK, "Library is in sync with lockfile\n")
    } else {
      cat(SYM_WARN, "Library out of sync with lockfile\n")
      cat("   Run renv::restore() to sync local environment\n")
    }
  }, error = function(e) {
    cat(SYM_CROSS, "Error checking status:", conditionMessage(e), "\n")
    issues <<- c(issues, "renv status check failed")
  })
} else {
  cat("- renv not available\n")
}
cat("\n")

# Section 4: Source:unknown check (using shared utility)
cat("--- Source:unknown Check ---\n")
if (file.exists("renv.lock")) {
  unknown_pkgs <- parse_unknown_sources("renv.lock")

  if (length(unknown_pkgs) == 0) {
    cat(SYM_CHECK, "No packages with Source:unknown\n")
  } else {
    cat(SYM_CROSS, length(unknown_pkgs), "package(s) with Source:unknown:\n")
    for (pkg in unknown_pkgs) {
      cat("   -", pkg, "\n")
    }
    issues <- c(issues, paste("Source:unknown packages:", paste(unknown_pkgs, collapse = ", ")))
  }
} else {
  cat("? renv.lock not found\n")
  issues <- c(issues, "renv.lock not found - run: renv::init()")
}
cat("\n")

# Section 5: Repository configuration
cat("--- Repository Configuration ---\n")
repos <- getOption("repos")
for (name in names(repos)) {
  cat(" ", name, ":", repos[[name]], "\n")
}
cat("\n")

# Section 6: Full diagnostics (optional, verbose only)
if (verbose) {
  cat("--- Full renv Diagnostics ---\n")
  cat("(This may take a moment...)\n\n")
  tryCatch({
    renv::diagnostics()
  }, error = function(e) {
    cat(SYM_CROSS, "Error running diagnostics:", conditionMessage(e), "\n")
  })
  cat("\n")
} else {
  cat("--- Full Diagnostics ---\n")
  cat("Run with --verbose flag for full renv::diagnostics() output\n\n")
}

# Summary with exit code
cat("=== Summary ===\n")
if (length(issues) == 0) {
  cat(SYM_CHECK, "No issues detected!\n")
  cat("\nReady to deploy. Run pre-deploy check to confirm:\n")
  cat("  Rscript", skill_script_path("pre_deploy_check.R", script_dir), "\n")
  quit(status = 0)
} else {
  cat(SYM_CROSS, length(issues), "issue(s) found:\n")
  for (i in seq_along(issues)) {
    cat("  ", i, ". ", issues[i], "\n", sep = "")
  }
  cat("\nSuggested fixes:\n")
  cat("  - Fix Source:unknown: Rscript", skill_script_path("fix_unknown_sources.R", script_dir), "--dry-run\n")
  cat("  - Regenerate manifest: Rscript", skill_script_path("regenerate_manifest.R", script_dir), "\n")
  quit(status = 1)
}
