#!/usr/bin/env bash
#
# College Calendar Automation Pipeline
# This script runs the complete end-to-end workflow:
# 1. Scrape HTML pages from college website
# 2. Generate ICS calendar files
# 3. Commit changes to git
# 4. Push to GitHub (for GitHub Pages hosting)
#
# Usage:
#   ./run_pipeline.sh           # Full run with git operations
#   ./run_pipeline.sh --dry-run # Skip git operations
#

set -euo pipefail

# Parse arguments
DRY_RUN=false
for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            ;;
    esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Logging
LOG_FILE="${SCRIPT_DIR}/logs/pipeline.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} - $1" | tee -a "$LOG_FILE"
}

error() {
    log "${RED}ERROR: $1${NC}"
}

success() {
    log "${GREEN}SUCCESS: $1${NC}"
    if command -v dunstify &> /dev/null; then
        dunstify -u normal -a "College Calendar" "Pipeline Success" "$1"
    fi
}

info() {
    log "${YELLOW}INFO: $1${NC}"
}

# Error handler
handle_error() {
    error "Pipeline failed at step: $1"
    if command -v dunstify &> /dev/null; then
        dunstify -u critical -a "College Calendar" "Pipeline Failed" "Step: $1\nCheck logs/pipeline.log for details."
    fi
    exit 1
}

# Main pipeline
main() {
    if [[ "$DRY_RUN" == "true" ]]; then
        log "Starting College Calendar Pipeline [DRY RUN] - $(date '+%Y-%m-%d %H:%M:%S')"
    else
        log "Starting College Calendar Pipeline - $(date '+%Y-%m-%d %H:%M:%S')"
    fi

    # Check if uv is available
    if ! command -v uv &> /dev/null; then
        if command -v dunstify &> /dev/null; then
            dunstify -u critical -a "College Calendar" "Pipeline Error" "uv is not installed or not in PATH."
        fi
        error "uv is not installed or not in PATH."
        error "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi

    # Check if .env exists
    if [[ ! -f "$SCRIPT_DIR/.env" ]]; then
        if command -v dunstify &> /dev/null; then
            dunstify -u critical -a "College Calendar" "Configuration Error" ".env file not found!"
        fi
        error ".env file not found!"
        error "Copy .env.example to .env and fill in your credentials:"
        error "  cp .env.example .env"
        error "  # Then edit .env with your username and password"
        exit 1
    fi

    # Step 0: Refresh session cookies
    log "Refreshing session cookies..."
    if ! uv run python "$SCRIPT_DIR/refresh_cookies.py" >> "$LOG_FILE" 2>&1; then
        handle_error "Cookie Refresh (check credentials in .env)"
    fi

    # Check if we're in a git repo (only if not dry run)
    if [[ "$DRY_RUN" == "false" ]] && [[ ! -d "$SCRIPT_DIR/.git" ]]; then
        error "Not a git repository!"
        exit 1
    fi

    # Step 1: Scrape HTML pages (capture output, only show on error)
    if ! uv run python "$SCRIPT_DIR/college_calender.py" >> "$LOG_FILE" 2>&1; then
        handle_error "HTML Scraping"
    fi

    # Step 2: Parse HTML to JSON (capture output, only show on error)
    if ! uv run python "$SCRIPT_DIR/parse_html.py" >> "$LOG_FILE" 2>&1; then
        handle_error "HTML Parsing"
    fi

    # Step 2.5: Validate RULES.toml against actual classes
    log "Validating RULES.toml configuration..."
    if ! uv run python "$SCRIPT_DIR/validate_rules.py"; then
        handle_error "RULES.toml Validation"
    fi

    # Step 3: Generate ICS files (capture output, only show on error)
    if ! uv run python "$SCRIPT_DIR/generate_ics.py" --split >> "$LOG_FILE" 2>&1; then
        handle_error "ICS Generation"
    fi

    # Exit here if dry run
    if [[ "$DRY_RUN" == "true" ]]; then
        success "Pipeline completed [DRY RUN] - ICS files generated (git operations skipped)"
        exit 0
    fi

    # Step 3: Check if there are any changes
    if git diff --quiet *.ics 2>/dev/null; then
        log "Pipeline completed - no changes detected"
        exit 0
    fi

    # Step 4: Commit and push changes
    git add F2F.ics Zoom.ics Rom.ics

    COMMIT_MSG="Update calendar files - $(date '+%Y-%m-%d %H:%M')"
    if ! git commit -m "$COMMIT_MSG

🤖 Automated update via systemd timer" >> "$LOG_FILE" 2>&1; then
        error "Git commit failed. Check $LOG_FILE for details."
        exit 1
    fi

    if ! git push >> "$LOG_FILE" 2>&1; then
        error "Git push failed. Your changes are committed locally but not pushed."
        error "Check $LOG_FILE for details. Common issues:"
        error "  - No network connection"
        error "  - SSH key not set up (try: ssh -T git@github.com)"
        error "  - No push permissions to remote repository"
        error "To retry manually: cd $SCRIPT_DIR && git push"
        exit 1
    fi

    success "Pipeline completed successfully - changes pushed to GitHub"
}

# Run main function
main "$@"
