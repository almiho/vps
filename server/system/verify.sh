#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------------------------------
# server/system/verify.sh
# Verifies the expected baseline system configuration is in place.
# Run as root or with sudo.
# Exits non-zero if any check fails.
# -----------------------------------------------------------------------------

# --- Colors -------------------------------------------------------------------

GREEN="\033[0;32m"
RED="\033[0;31m"
BLUE="\033[0;34m"
GRAY="\033[0;90m"
NC="\033[0m"

# --- Logging helpers ----------------------------------------------------------

info()    { echo -e "${GRAY}[INFO]  $*${NC}"; }
pass()    { echo -e "${GREEN}[PASS]${NC}  $*"; }
fail()    { echo -e "${RED}[FAIL]${NC}  $*" >&2; FAILED=1; }

FAILED=0

# --- Preflight ----------------------------------------------------------------

if [[ "$(id -u)" -ne 0 ]]; then
  echo "[FAIL]  This script must be run as root (use sudo)." >&2
  exit 1
fi

info "Starting baseline system verification..."
echo -e "${BLUE}$(date '+%A, %Y-%m-%d %H:%M:%S')${NC}"
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

# --- UFW: SSH must NOT be open publicly ---------------------------------------

info "Checking UFW rules..."

if ufw status | grep -qiE '(22/tcp|OpenSSH).*ALLOW IN'; then
  fail "UFW: SSH (22/tcp) is publicly open — should be Tailscale only"
else
  pass "UFW: SSH (22/tcp) not publicly reachable"
fi

# --- UFW: Tailscale interface allowed -----------------------------------------

if ufw status | grep -qi "tailscale0"; then
  pass "UFW: tailscale0 interface allowed"
else
  fail "UFW: tailscale0 not found in UFW rules (SSH unreachable without this)"
fi

echo

# --- Tailscale: service running -----------------------------------------------

info "Checking Tailscale..."

if systemctl is-active --quiet tailscaled; then
  pass "Tailscale: tailscaled service is active"
else
  fail "Tailscale: tailscaled service is not active (SSH access may be lost)"
fi

if tailscale status --self 2>/dev/null | grep -q "100\."; then
  pass "Tailscale: connected ($(tailscale ip -4 2>/dev/null))"
else
  fail "Tailscale: not connected — run 'tailscale up'"
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
  echo -e "${RED}[FAIL]${NC}  One or more checks failed. See output above." >&2
  exit 1
fi

echo -e "${GREEN}[OK]${NC}    All baseline system checks passed."
