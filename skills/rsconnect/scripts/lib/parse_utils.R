# Shared utilities for rsconnect helper scripts
# Source this file: source(file.path(dirname(sys.frame(1)$ofile), "lib", "parse_utils.R"))

# Unicode symbols for consistent output
SYM_CHECK <- "\u2713"
SYM_CROSS <- "\u2717"
SYM_WARN <- "\u26a0"

#' Parse renv.lock and find packages with Source: unknown
#'
#' @param lock_path Path to renv.lock file (default: "renv.lock")
#' @return Character vector of package names with Source: unknown, or empty vector
parse_unknown_sources <- function(lock_path = "renv.lock") {
  if (!file.exists(lock_path)) {
    return(character())
  }

  lock_content <- readLines(lock_path, warn = FALSE)
  unknown_lines <- grep('"Source":\\s*"unknown"', lock_content)

  if (length(unknown_lines) == 0) {
    return(character())
  }

  # Extract package names by looking backwards from each Source: unknown line

unknown_pkgs <- vapply(unknown_lines, function(line_num) {
    for (i in seq(line_num, max(1, line_num - 10), by = -1)) {
      if (grepl('"Package":', lock_content[i])) {
        return(sub('.*"Package":\\s*"([^"]+)".*', "\\1", lock_content[i]))
      }
    }
    NA_character_
  }, character(1), USE.NAMES = FALSE)

  unique(unknown_pkgs[!is.na(unknown_pkgs)])
}

#' Get package version from renv.lock
#'
#' @param pkg_name Package name to look up
#' @param lock_path Path to renv.lock file (default: "renv.lock")
#' @return Version string or NULL if not found
get_package_version <- function(pkg_name, lock_path = "renv.lock") {
  if (!file.exists(lock_path)) {
    return(NULL)
  }

  lock_content <- readLines(lock_path, warn = FALSE)
  pkg_pattern <- paste0('"Package":\\s*"', pkg_name, '"')
  pkg_line <- grep(pkg_pattern, lock_content)

  if (length(pkg_line) == 0) {
    return(NULL)
  }

  # Look for Version in subsequent lines (within the same package block)
  for (i in seq(pkg_line[1], min(length(lock_content), pkg_line[1] + 15))) {
    if (grepl('"Version":', lock_content[i])) {
      return(sub('.*"Version":\\s*"([^"]+)".*', "\\1", lock_content[i]))
    }
    # Stop if we hit another package block
    if (i > pkg_line[1] && grepl('"Package":', lock_content[i])) {
      break
    }
  }

  NULL
}

#' Count packages with Source: unknown
#'
#' @param lock_path Path to renv.lock file (default: "renv.lock")
#' @return Integer count
count_unknown_sources <- function(lock_path = "renv.lock") {
  length(parse_unknown_sources(lock_path))
}

#' Check if renv.lock exists and is valid JSON
#'
#' @param lock_path Path to renv.lock file (default: "renv.lock")
#' @return List with $valid (logical) and $error (character or NULL)
validate_lockfile <- function(lock_path = "renv.lock") {
  if (!file.exists(lock_path)) {
    return(list(valid = FALSE, error = "File not found"))
  }

  tryCatch({
    jsonlite::fromJSON(lock_path)
    list(valid = TRUE, error = NULL)
  }, error = function(e) {
    list(valid = FALSE, error = conditionMessage(e))
  })
}

#' Print a boxed header for script output
#'
#' @param title Title to display in the box
#' @param width Box width (default: 40)
box_header <- function(title, width = 40) {
  # Ensure title fits
title <- substr(title, 1, width - 4)
  padding <- width - nchar(title) - 4

  cat("\n")
  cat(paste0("\u2554", paste(rep("\u2550", width - 2), collapse = ""), "\u2557\n"))
  cat(paste0("\u2551  ", title, paste(rep(" ", padding), collapse = ""), "\u2551\n"))
  cat(paste0("\u255a", paste(rep("\u2550", width - 2), collapse = ""), "\u255d\n"))
  cat("\n")
}

#' Print a boxed result (success or failure)
#'
#' @param success Logical indicating success or failure
#' @param width Box width (default: 40)
box_result <- function(success, width = 40) {
  cat("\n")
  cat(paste0("\u2554", paste(rep("\u2550", width - 2), collapse = ""), "\u2557\n"))
  if (success) {
    msg <- paste0(SYM_CHECK, " READY TO DEPLOY")
  } else {
    msg <- paste0(SYM_CROSS, " ISSUES FOUND")
  }
  padding <- width - nchar(msg) - 4
  cat(paste0("\u2551  ", msg, paste(rep(" ", max(0, padding)), collapse = ""), "\u2551\n"))
  cat(paste0("\u255a", paste(rep("\u2550", width - 2), collapse = ""), "\u255d\n"))
}

#' Get the script's directory (for sourcing relative files)
#'
#' @return Directory path of the currently running script
get_script_dir <- function() {
  # Try multiple methods to find script location
  args <- commandArgs(trailingOnly = FALSE)
  file_arg <- grep("^--file=", args, value = TRUE)

if (length(file_arg) > 0) {
    return(dirname(normalizePath(sub("^--file=", "", file_arg[1]))))
  }

  # Fallback for sourced scripts
  if (!is.null(sys.frame(1)$ofile)) {
    return(dirname(sys.frame(1)$ofile))
  }

  # Last resort: current directory
  getwd()
}
