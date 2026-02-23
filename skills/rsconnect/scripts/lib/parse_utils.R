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

  if (requireNamespace("jsonlite", quietly = TRUE)) {
    parsed <- tryCatch(
      jsonlite::fromJSON(lock_path, simplifyVector = FALSE),
      error = function(e) NULL
    )
    if (!is.null(parsed) && !is.null(parsed$Packages) && is.list(parsed$Packages)) {
      pkgs <- parsed$Packages
      if (!is.null(names(pkgs))) {
        unknown_pkgs <- names(pkgs)[vapply(pkgs, function(pkg) {
          is.list(pkg) && identical(pkg$Source, "unknown")
        }, logical(1))]
        return(unique(unknown_pkgs))
      }
    }
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

#' Get the skill root directory (agent-agnostic)
#'
#' Computes the skill root by walking up from the script's location.
#' Works regardless of where the skill is installed:
#'   .claude/skills/rsconnect/, .cursor/skills/rsconnect/, etc.
#'
#' @param from_dir Directory to resolve from (default: auto-detect via get_script_dir())
#' @return Absolute path to the skill root directory
get_skill_root <- function(from_dir = NULL) {
  if (is.null(from_dir)) {
    from_dir <- get_script_dir()
  }

  # Walk up from scripts/lib/ -> scripts/ -> skill root
  # Or from scripts/ -> skill root
  dir <- normalizePath(from_dir, mustWork = FALSE)
  if (basename(dir) == "lib") {
    dir <- dirname(dir)  # lib/ -> scripts/
  }
  if (basename(dir) == "scripts") {
    dir <- dirname(dir)  # scripts/ -> skill root
  }
  dir
}

#' Build full path to a skill script (agent-agnostic)
#'
#' Returns the full path for a script relative to the skill root,
#' suitable for display in output messages.
#'
#' @param script_name Script filename (e.g., "fix_unknown_sources.R")
#' @param from_dir Directory to resolve from (default: auto-detect)
#' @return Relative path from working directory to the script
skill_script_path <- function(script_name, from_dir = NULL) {
  root <- get_skill_root(from_dir)
  full_path <- file.path(root, "scripts", script_name)

  # Return path relative to working directory for cleaner output
  wd <- normalizePath(getwd(), mustWork = FALSE)
  full_norm <- normalizePath(full_path, mustWork = FALSE)

  # Try to make it relative
  if (startsWith(full_norm, wd)) {
    rel <- substring(full_norm, nchar(wd) + 2)  # +2 to skip trailing /
    if (nchar(rel) > 0) return(rel)
  }

  full_path
}

#' Check if the agent skill directory is listed in .gitignore
#'
#' Detects the top-level agent directory (e.g. .cursor, .agents, .claude)
#' from the running script's path, then checks if .gitignore covers it.
#'
#' @param from_dir Directory to resolve from (default: auto-detect)
#' @return List with $ignored (logical) and $agent_dir (character or NULL)
check_skill_dir_gitignored <- function(from_dir = NULL) {
  skill_root <- get_skill_root(from_dir)
  wd <- normalizePath(getwd(), mustWork = FALSE)
  skill_norm <- normalizePath(skill_root, mustWork = FALSE)

  # Get relative path from working directory
  if (!startsWith(skill_norm, wd)) {
    return(list(ignored = TRUE, agent_dir = NULL))
  }

  rel <- substring(skill_norm, nchar(wd) + 2)
  if (nchar(rel) == 0) {
    return(list(ignored = TRUE, agent_dir = NULL))
  }

  # The agent dir is the first path component (e.g. ".cursor")
  parts <- strsplit(rel, .Platform$file.sep)[[1]]
  if (length(parts) == 0) {
    return(list(ignored = TRUE, agent_dir = NULL))
  }
  agent_dir <- parts[1]

  # Only check hidden directories (agent conventions)
  if (!startsWith(agent_dir, ".")) {
    return(list(ignored = TRUE, agent_dir = NULL))
  }

  # Check .gitignore
  gitignore_path <- ".gitignore"
  if (!file.exists(gitignore_path)) {
    return(list(ignored = FALSE, agent_dir = agent_dir))
  }

  lines <- readLines(gitignore_path, warn = FALSE)
  lines <- trimws(lines)
  patterns <- c(agent_dir, paste0(agent_dir, "/"),
                paste0("/", agent_dir), paste0("/", agent_dir, "/"))
  agent_pattern <- gsub("([\\\\.\\+\\*\\?\\^\\$\\(\\)\\[\\]\\{\\}\\|])", "\\\\\\1", agent_dir)
  regex <- paste0("(^|.*/)", agent_pattern, "(/|$)")

  matches <- vapply(lines, function(line) {
    if (line == "" || startsWith(line, "#") || startsWith(line, "!")) {
      return(FALSE)
    }
    if (line %in% patterns) {
      return(TRUE)
    }
    normalized <- sub("/+$", "", line)
    if (normalized %in% c(agent_dir, paste0("/", agent_dir))) {
      return(TRUE)
    }
    grepl(regex, line)
  }, logical(1))

  if (any(matches)) {
    return(list(ignored = TRUE, agent_dir = agent_dir))
  }

  list(ignored = FALSE, agent_dir = agent_dir)
}
