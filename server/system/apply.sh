#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------------------------------
# server/system/apply.sh
# Idempotent baseline system configuration for the VPS.
# Run as root or with sudo.
# -----------------------------------------------------------------------------

# --- Logging helpers ----------------------------------------------------------

info()    { echo "[INFO]  $*"; }
success() { echo "[OK]    $*"; }
warn()    { echo "[WARN]  $*"; }
fail()    { echo "[FAIL]  $*" >&2; exit 1; }

# --- Preflight ----------------------------------------------------------------

if [[ "$(id -u)" -ne 0 ]]; then
  fail "This script must be run as root (use sudo)."
fi

info "Starting baseline system apply..."

# --- SSH ----------------------------------------------------------------------
# No changes made yet. SSH hardening is already applied manually.
# Future: enforce /etc/ssh/sshd_config.d/99-baseline.conf here.

info "SSH: no changes applied (hardening already in place)."

# --- UFW ----------------------------------------------------------------------
# No changes made yet. UFW rules are already configured.
# Future: enforce default deny, allow SSH, reload UFW here.

info "UFW: no changes applied (rules already in place)."

# --- fail2ban -----------------------------------------------------------------
# No changes made yet. fail2ban is already installed and active.
# Future: enforce jail config and reload here.

info "fail2ban: no changes applied (service already in place)."

# --- Done ---------------------------------------------------------------------

success "Baseline system apply complete. Nothing changed (skeleton run)."
