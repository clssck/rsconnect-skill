#!/usr/bin/env Rscript
# Regenerate manifest.json for Posit Connect Git-backed deployment

# Source shared utilities
script_dir <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1]))
if (length(script_dir) == 0 || is.na(script_dir)) script_dir <- "."
source(file.path(script_dir, "lib", "parse_utils.R"))

# Increase file limit to handle large applications (default is 1000)
# Typical Shiny apps with renv can have 2000-4000 files
options(rsconnect.max.bundle.files = 5000)

box_header("REGENERATE MANIFEST")

# Check rsconnect is available
if (!requireNamespace("rsconnect", quietly = TRUE)) {
  cat(SYM_CROSS, "rsconnect not installed\n")
  cat("Run: install.packages('rsconnect')\n")
  quit(status = 1)
}

cat("rsconnect version:", as.character(packageVersion("rsconnect")), "\n")
cat("Bundle file limit:", getOption("rsconnect.max.bundle.files"), "\n\n")

cat("Generating manifest.json... ")

tryCatch({
  rsconnect::writeManifest()

  # Verify manifest was created
  if (file.exists("manifest.json")) {
    cat(SYM_CHECK, "\n\n")
    box_result(TRUE)
    cat("\nmanifest.json regenerated successfully\n")
    cat("\nNext steps:\n")
    cat("  1. Run pre-deploy check: Rscript .claude/skills/rsconnect/scripts/pre_deploy_check.R\n")
    cat("  2. Commit: git add manifest.json renv.lock && git commit -m 'chore: update manifest'\n")
    cat("  3. Push to trigger deployment\n")
    quit(status = 0)
  } else {
    cat(SYM_CROSS, "\n")
    cat("writeManifest() succeeded but manifest.json not found\n")
    quit(status = 1)
  }
}, error = function(err) {
  cat(SYM_CROSS, "\n\n")
  box_result(FALSE)
  cat("\nFailed to regenerate manifest.json\n")
  cat("Error:", conditionMessage(err), "\n\n")
  cat("Common causes:\n")
  cat("  - .rscignore excluding critical files (check patterns)\n")
  cat("  - Missing dependencies in renv.lock (run renv::status())\n")
  cat("  - Package with Source:unknown (run fix_unknown_sources.R)\n")
  cat("  - No app entry point (app.R, server.R, or *.Rmd)\n")
  quit(status = 1)
})
