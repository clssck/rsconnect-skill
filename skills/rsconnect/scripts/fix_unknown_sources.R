#!/usr/bin/env Rscript
# Finds and fixes packages with Source:unknown in renv.lock
# SAFETY FEATURES: --dry-run mode, automatic backup, version preservation

# Parse command line arguments
args <- commandArgs(trailingOnly = TRUE)
dry_run <- "--dry-run" %in% args || "-n" %in% args
help_requested <- "--help" %in% args || "-h" %in% args

if (help_requested) {
  cat("Usage: Rscript fix_unknown_sources.R [OPTIONS]\n\n")
  cat("Options:\n")
  cat("  --dry-run, -n  Show what would be done without making changes\n")
  cat("  --help, -h     Show this help message\n")
  cat("\nThis script:\n")
  cat("  1. Finds packages with Source:unknown in renv.lock\n")
  cat("  2. Creates a timestamped backup of renv.lock\n")
  cat("  3. Reinstalls each package from CRAN (preserving version)\n")
  cat("  4. Updates renv.lock via renv::snapshot()\n")
  quit(status = 0)
}

# Source shared utilities
script_dir <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1]))
if (length(script_dir) == 0 || is.na(script_dir)) script_dir <- "."
source(file.path(script_dir, "lib", "parse_utils.R"))

box_header("FIX SOURCE:UNKNOWN")

if (dry_run) {
  cat(">>> DRY RUN MODE - No changes will be made <<<\n\n")
}

# Check renv.lock exists
if (!file.exists("renv.lock")) {
  cat(SYM_CROSS, "renv.lock not found\n")
  quit(status = 1)
}

# Find packages with Source:unknown using shared utility
unknown_pkgs <- parse_unknown_sources("renv.lock")

if (length(unknown_pkgs) == 0) {
  cat(SYM_CHECK, "No packages with Source:unknown found!\n")
  quit(status = 0)
}

cat("Found", length(unknown_pkgs), "package(s) with Source:unknown:\n")
for (pkg in unknown_pkgs) {
  version <- get_package_version(pkg, "renv.lock")
  if (!is.null(version)) {
    cat("  -", pkg, "@", version, "\n", sep = "")
  } else {
    cat("  -", pkg, "(version unknown)\n")
  }
}
cat("\n")

# Create backup before any modifications
if (!dry_run) {
  backup_name <- paste0("renv.lock.backup.", format(Sys.time(), "%Y%m%d_%H%M%S"))
  cat("Creating backup:", backup_name, "... ")
  tryCatch({
    file.copy("renv.lock", backup_name)
    cat(SYM_CHECK, "\n")
  }, error = function(e) {
    cat(SYM_CROSS, "Failed to create backup:", conditionMessage(e), "\n")
    cat("Aborting for safety. Fix manually or run with --dry-run first.\n")
    quit(status = 1)
  })
}

# Ensure renv is available
if (!requireNamespace("renv", quietly = TRUE)) {
  cat(SYM_CROSS, "renv package not available\n")
  quit(status = 1)
}

# Reinstall each package, preserving version from renv.lock
cat("\nReinstalling packages", if (dry_run) "(DRY RUN)" else "", "...\n\n")
failed_pkgs <- character()

for (pkg in unknown_pkgs) {
  version <- get_package_version(pkg, "renv.lock")
  pkg_spec <- if (!is.null(version)) paste0(pkg, "@", version) else pkg

  cat("  ", pkg_spec, "... ", sep = "")

  if (dry_run) {
    cat("[would install]\n")
  } else {
    tryCatch({
      suppressMessages(renv::install(pkg_spec, prompt = FALSE))
      cat(SYM_CHECK, "\n")
    }, error = function(e) {
      cat(SYM_CROSS, "Failed\n")
      cat("    Error:", conditionMessage(e), "\n")
      failed_pkgs <<- c(failed_pkgs, pkg)
    })
  }
}

cat("\n")

# Resnapshot to update renv.lock
if (!dry_run) {
  cat("Updating renv.lock... ")
  snapshot_success <- FALSE
  tryCatch({
    suppressMessages(renv::snapshot(prompt = FALSE))
    snapshot_success <- TRUE
    cat(SYM_CHECK, "\n")
  }, error = function(e) {
    cat(SYM_CROSS, "Failed:", conditionMessage(e), "\n")
    cat("\nSnapshot failed. Your backup is at:", backup_name, "\n")
    cat("To restore: cp", backup_name, "renv.lock\n")
  })

  if (!snapshot_success) {
    quit(status = 1)
  }
}

# Verify fix
cat("\nVerifying", if (dry_run) "(skipped in dry-run)" else "", "... ")

if (dry_run) {
  cat("\n\n")
  box_result(TRUE)
  cat("\nDry run complete. Run without --dry-run to apply changes.\n")
  quit(status = 0)
}

remaining <- parse_unknown_sources("renv.lock")

if (length(remaining) == 0) {
  cat(SYM_CHECK, "All Source:unknown issues resolved!\n\n")
  box_result(TRUE)
  cat("\nNext steps:\n")
  cat("  1. Regenerate manifest: Rscript .claude/skills/rsconnect/scripts/regenerate_manifest.R\n")
  cat("  2. Run pre-deploy check: Rscript .claude/skills/rsconnect/scripts/pre_deploy_check.R\n")
  cat("\nBackup saved at:", backup_name, "(delete when satisfied)\n")
  quit(status = 0)
} else {
  cat(SYM_CROSS, length(remaining), "package(s) still have Source:unknown\n\n")
  box_result(FALSE)

  cat("\nManual intervention needed for:\n")
  for (pkg in failed_pkgs) {
    version <- get_package_version(pkg, "renv.lock")
    cat("  -", pkg, "\n")
    cat("    Try: renv::install('", pkg, if (!is.null(version)) paste0("@", version) else "", "')\n", sep = "")
    cat("    Or from RSPM: options(repos = c(CRAN = 'https://packagemanager.posit.co/cran/latest'))\n")
  }
  cat("\nTo restore original: cp", backup_name, "renv.lock\n")
  quit(status = 1)
}
