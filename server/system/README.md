# server/system

Baseline system configuration for the VPS.

This folder owns the foundational security and service layer of the server:
SSH hardening, firewall rules (UFW), and intrusion prevention (fail2ban).
It does not manage application-level services; those live in their own subdirectories.

## Scripts

### `apply.sh`

Applies the baseline system configuration idempotently.
Safe to run multiple times; each action checks current state before making changes.

```bash
sudo ./server/system/apply.sh
```

> Currently a skeleton. Future actions (SSH config enforcement, UFW rule management,
> fail2ban tuning) will be added here incrementally.

### `verify.sh`

Verifies that the expected baseline configuration is in place.
Exits non-zero and prints a clear error message if any check fails.

```bash
sudo ./server/system/verify.sh
```

Checks performed:
- `sshd` effective config: password auth off, pubkey on, root login hardened
- UFW active with default deny incoming
- UFW allows SSH (22/tcp) inbound
- fail2ban enabled and running
- fail2ban sshd jail present
