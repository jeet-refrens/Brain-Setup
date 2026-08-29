#!/usr/bin/env bash
# Linux setup: ensure Homebrew is present, then install everything via the Brewfile.
# Targets glibc distros (Ubuntu/Debian/Fedora/…); not Alpine/musl or containers.
# Idempotent — safe to re-run. macOS users: `just setup` runs `brew bundle` directly.

set -euo pipefail

log() { echo "==> $*"; }
have() { command -v "$1" >/dev/null 2>&1; }

# --- Homebrew ----------------------------------------------------------------
if ! have brew; then
  log "Homebrew not found — installing (https://brew.sh)"
  log "To install it yourself instead, run:"
  log '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
  NONINTERACTIVE=1 /bin/bash -c \
    "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Make brew available on PATH for the rest of this script (Linux installs to
# /home/linuxbrew/.linuxbrew; a custom prefix lands in ~/.linuxbrew).
if ! have brew; then
  for prefix in /home/linuxbrew/.linuxbrew "$HOME/.linuxbrew"; do
    [ -x "$prefix/bin/brew" ] && eval "$("$prefix/bin/brew" shellenv)" && break
  done
fi
have brew || { log "Homebrew install failed — add brew to PATH and re-run"; exit 1; }

# --- Dependencies (Brewfile) -------------------------------------------------
log "Installing dependencies via Brewfile"
brew bundle --file="$(dirname "$0")/../Brewfile"

log "Linux dependencies ready"
