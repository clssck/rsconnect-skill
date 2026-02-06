#!/usr/bin/env Rscript
# Pre-deploy validation for Posit Connect Git-backed deployments
# Checks: manifest, rsconnect version, Source:unknown, sync status

# Source shared utilities
script_dir <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1]))
if (length(script_dir) == 0 || is.na(script_dir)) script_dir <- "."
source(file.path(script_dir, "lib", "parse_utils.R"))

passed <- TRUE
issues <- character()
warnings <- character()

# Header
box_header("PRE-DEPLOY CHECK")

# Check 1: manifest.json exists
cat("1. Manifest file... ")
if (file.exists("manifest.json")) {
  cat(SYM_CHECK, "Present\n")
} else {
  cat(SYM_CROSS, "MISSING\n")
  issues <- c(issues, paste("Run: Rscript", skill_script_path("regenerate_manifest.R", script_dir)))
  passed <- FALSE
}

# Check 2: rsconnect package version
# rsconnect 0.8.15 introduced improved manifest generation required for Git-backed deploys
cat("2. rsconnect version... ")
if (requireNamespace("rsconnect", quietly = TRUE)) {
  version <- packageVersion("rsconnect")
  min_version <- package_version("0.8.15")  # Minimum for Git-backed deployment
  if (version >= min_version) {
    cat(SYM_CHECK, as.character(version), "\n")
  } else {
    cat(SYM_CROSS, as.character(version), "(need >= 0.8.15)\n")
    issues <- c(issues, "Run: install.packages('rsconnect')")
    passed <- FALSE
  }
} else {
  cat(SYM_CROSS, "Not installed\n")
  issues <- c(issues, "Run: install.packages('rsconnect')")
  passed <- FALSE
}

# Check 3: Source:unknown in renv.lock (using shared utility)
cat("3. Source:unknown packages... ")
if (file.exists("renv.lock")) {
  unknown_pkgs <- parse_unknown_sources("renv.lock")
  if (length(unknown_pkgs) == 0) {
    cat(SYM_CHECK, "None found\n")
  } else {
    cat(SYM_CROSS, length(unknown_pkgs), "found:", paste(unknown_pkgs, collapse = ", "), "\n")
    issues <- c(issues, paste("Run: Rscript", skill_script_path("fix_unknown_sources.R", script_dir)))
    passed <- FALSE
  }
} else {
  cat("? renv.lock not found (not using renv?)\n")
}

# Check 4: renv.lock and manifest.json in sync (with NA handling)
cat("4. Lockfile/manifest sync... ")
if (file.exists("manifest.json") && file.exists("renv.lock")) {
  manifest_mtime <- file.mtime("manifest.json")
  lock_mtime <- file.mtime("renv.lock")

  if (is.na(manifest_mtime) || is.na(lock_mtime)) {
    cat("? couldn't determine file times\n")
  } else if (manifest_mtime >= lock_mtime) {
    cat(SYM_CHECK, "manifest is up to date\n")
  } else {
    cat(SYM_WARN, "manifest may be stale (older than renv.lock)\n")
    warnings <- c(warnings, paste("Consider: Rscript", skill_script_path("regenerate_manifest.R", script_dir)))
  }
} else {
  cat("- Skipped (missing files)\n")
}

# Check 5: Local library sync (informational - doesn't block deployment)
cat("5. Local library sync... ")
if (requireNamespace("renv", quietly = TRUE)) {
  tryCatch({
    # Suppress renv's verbose output completely
    invisible(capture.output({
      result <- renv::status()
    }, type = "output"))
    invisible(capture.output({
      result <- result  # force evaluation
    }, type = "message"))

    # Check if there are any sync issues
    has_issues <- !is.null(result$library) && length(result$library$Packages) > 0
    if (has_issues) {
      cat(SYM_WARN, "out of sync (run renv::restore() to fix local env)\n")
      cat("   Note: This doesn't block deployment - Connect uses renv.lock\n")
    } else {
      cat(SYM_CHECK, "in sync\n")
    }
  }, error = function(e) {
    cat("? couldn't check\n")
  })
} else {
  cat("- renv not available\n")
}

# Summary
box_result(passed)

if (passed) {
  if (length(warnings) > 0) {
    cat("\nOptional improvements:\n")
    for (w in warnings) {
      cat("  -", w, "\n")
    }
  }
  quit(status = 0)
} else {
  cat("\nFixes needed:\n")
  for (issue in issues) {
    cat("  -", issue, "\n")
  }
  quit(status = 1)
}
