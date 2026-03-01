#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------------------------------
# server/system/verify.sh
# Verifies the expected baseline system configuration is in place.
# Run as root or with sudo.
# Exits non-zero if any check fails.
# -----------------------------------------------------------------------------

# --- Logging helpers ----------------------------------------------------------

info()    { echo "[INFO]  $*"; }
pass()    { echo "[PASS]  $*"; }
fail()    { echo "[FAIL]  $*" >&2; FAILED=1; }

FAILED=0

# --- Preflight ----------------------------------------------------------------

if [[ "$(id -u)" -ne 0 ]]; then
  echo "[FAIL]  This script must be run as root (use sudo)." >&2
  exit 1
fi

info "Starting baseline system verification..."
echo

# --- Helper: get sshd effective config value ---------------------------------

sshd_get() {
  local key="$1"
  local val
  val=$(sshd -T 2>/dev/null | grep -i "^${key} " | awk '{print $2}')
  if [[ -z "${val}" ]]; then
    fail "sshd: could not read value for '${key}' (sshd -T returned nothing — missing host keys or permission issue?)"
    echo ""
    return
  fi
  echo "${val}"
}

# --- SSH: effective sshd config -----------------------------------------------

info "Checking sshd effective configuration..."

val=$(sshd_get "passwordauthentication")
if [[ "${val}" == "no" ]]; then
  pass "sshd: PasswordAuthentication no"
else
  fail "sshd: PasswordAuthentication expected 'no', got '${val}'"
fi

val=$(sshd_get "kbdinteractiveauthentication")
if [[ "${val}" == "no" ]]; then
  pass "sshd: KbdInteractiveAuthentication no"
else
  fail "sshd: KbdInteractiveAuthentication expected 'no', got '${val}'"
fi

val=$(sshd_get "pubkeyauthentication")
if [[ "${val}" == "yes" ]]; then
  pass "sshd: PubkeyAuthentication yes"
else
  fail "sshd: PubkeyAuthentication expected 'yes', got '${val}'"
fi

val=$(sshd_get "permitrootlogin")
if [[ "${val}" =~ ^(no|without-password|prohibit-password)$ ]]; then
  pass "sshd: PermitRootLogin hardened ('${val}')"
else
  fail "sshd: PermitRootLogin expected no/without-password/prohibit-password, got '${val}'"
fi

echo

# --- UFW: active and default deny incoming ------------------------------------

info "Checking UFW status..."

if ufw status | grep -qi "Status: active"; then
  pass "UFW: active"
else
  fail "UFW: not active"
fi

if ufw status verbose | grep -qi "Default: deny (incoming)"; then
  pass "UFW: default deny incoming"
else
  fail "UFW: default incoming policy is not 'deny'"
fi

echo

# --- UFW: SSH inbound allowed -------------------------------------------------

info "Checking UFW rules..."

# Use verbose output for consistent rule formatting
if ufw status verbose | grep -qiE '(22/tcp|OpenSSH).*ALLOW IN'; then
  pass "UFW: SSH allowed inbound"
else
  fail "UFW: SSH inbound rule not found"
fi

echo

# --- fail2ban: service state --------------------------------------------------

info "Checking fail2ban service..."

if systemctl is-active --quiet fail2ban; then
  pass "fail2ban: service is active"
else
  fail "fail2ban: service is not active"
fi

if systemctl is-enabled --quiet fail2ban; then
  pass "fail2ban: service is enabled"
else
  fail "fail2ban: service is not enabled (will not start on boot)"
fi

echo

# --- fail2ban: sshd jail ------------------------------------------------------

info "Checking fail2ban sshd jail..."

if fail2ban-client status 2>/dev/null | grep -q "sshd"; then
  pass "fail2ban: sshd jail listed in active jails"
else
  fail "fail2ban: sshd not listed in active jails (check /etc/fail2ban/jail.local)"
fi

if fail2ban-client status sshd >/dev/null 2>&1; then
  pass "fail2ban: sshd jail is present and active"
else
  fail "fail2ban: sshd jail status check failed (check /etc/fail2ban/jail.local)"
fi

echo

# --- Result -------------------------------------------------------------------

if [[ "${FAILED}" -ne 0 ]]; then
  echo "[FAIL]  One or more checks failed. See output above." >&2
  exit 1
fi

echo "[OK]    All baseline system checks passed."
