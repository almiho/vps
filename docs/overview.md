# VPS Project Overview

## Purpose

This repository manages a personal VPS that serves multiple purposes.
It is not a single-app server — it is an evolving personal infrastructure platform.

## What runs on the VPS

### 1. OpenClaw — personal AI assistant (primary purpose)

OpenClaw is the main reason this VPS exists.
The goal is to build a personal AI assistant that:

- Runs 24/7 and proactively reaches out (no need to open a chat tab)
- Is reachable via **WhatsApp** (primary), with Telegram as an alternative
- Covers multiple life domains incrementally: calendar, email, tasks, finances, news, etc.
- Has memory and tools, not just a chat interface
- Can be extended step by step with new capabilities over time

### 2. relaxedon.boats — web application

A simple web server hosting a small app for boat owners.
The app helps boat owners find and manage services around their boats.
This runs alongside OpenClaw on the same VPS and is independently accessible.

### 3. Future services (TBD)

The VPS is intentionally multi-purpose.
Additional services may be added over time, each in its own directory under `server/`.

---

## Repository structure

```
vps/
├── server/                  # Everything that runs on the VPS
│   ├── system/              # Baseline OS config (SSH, UFW, fail2ban)
│   ├── openclaw/            # OpenClaw deployment
│   └── docker/              # Docker-based services
├── external/                # Tooling and tests run from outside the VPS
│   └── tests/               # pytest-based external checks (SSH, etc.)
└── docs/                    # Project documentation
```

---

## Infrastructure approach

### Docker — one container per service

All services on the VPS run in Docker containers.
Each service gets its own container; they communicate over Docker's internal network.
No service shares a container with another.

Example layout:

| Container | Purpose |
|---|---|
| `openclaw` | OpenClaw AI assistant |
| `relaxedon-boats` | Web app (nginx + app) |
| `reverse-proxy` | Traefik or nginx — handles 80→443, SSL termination for all web services |

Container definitions live in `docker-compose.yml` files inside each service directory under `server/`.
This keeps everything version-controlled and reproducible.

### Hostinger Docker Manager GUI — not the primary tool

Hostinger provides a Docker Manager GUI through its web panel.
It was used for the initial OpenClaw one-click deploy and can serve as an emergency fallback.
However, it is **not** the primary way to manage containers on this VPS.

Reason: the GUI limits configuration options and cannot be version-controlled.
All ongoing container management is done via `docker-compose` files in this repository,
deployed over SSH (and eventually Tailscale).

### Tailscale — host-level, not containerised

Tailscale runs directly on the **VPS host OS**, not inside a container.
It requires access to the kernel network stack (TUN interface) which containers cannot provide cleanly.

Benefit: all containers automatically benefit from Tailscale without any per-container setup.
Binding a container port to the Tailscale IP (e.g. `100.x.x.x:3000`) makes it private automatically.

---

## Security model

Security is a top priority. The attack surface should be minimal.

### Principle

> The only publicly reachable services are the ones that **must** be public.
> Everything else is private, accessible only over Tailscale.

### Tailscale (target architecture)

[Tailscale](https://tailscale.com) creates a private WireGuard-based overlay network.
The goal is to route all private access (SSH, OpenClaw dashboard) through Tailscale,
so those services are invisible to the public internet.

| Service | Access | Notes |
|---|---|---|
| SSH | **Tailscale only** | Port 22 closed to public internet |
| OpenClaw dashboard | **Tailscale only** | Not publicly reachable |
| WhatsApp / Telegram bot | Outbound only | Server calls out — no inbound port needed |
| relaxedon.boats web app | **Public** (80/443) | Only intentionally public service |

### Baseline hardening (already in place)

- SSH: key-only auth, no passwords, no root login
- UFW: default deny incoming, allow outgoing
- fail2ban: active with sshd jail

### Scripts

- `server/system/verify.sh` — audits the current baseline config
- `server/system/apply.sh` — applies/enforces baseline config (skeleton, to be built out)

---

## Current state (as of Apr 2026)

### Infrastructure

| Component | Status | Notes |
|---|---|---|
| Ubuntu 24.04 | ✅ Running | Kernel upgrade pending — reboot needed |
| SSH hardening | ✅ Done | Key-only, no passwords, no root login |
| UFW | ✅ Done | Default deny; Tailscale allowed; 80+443 public |
| fail2ban | ✅ Running | sshd jail active |
| Tailscale | ✅ Running | VPS IP: `100.67.100.125`; host-level install |
| SSH via Tailscale only | ✅ Done | Port 22 closed to public internet |

### Services

| Service | Status | Notes |
|---|---|---|
| `relaxedon.boats` wireframe | ✅ Running | Caddy container, password-protected, ports 80+443 |
| OpenClaw | ✅ Running | Docker host network, Tailscale-only, Telegram connected |

### SSH config (local Mac)

| Alias | Host | Notes |
|---|---|---|
| `ssh vps` | `100.67.100.125` (Tailscale) | Primary — key auth, no passphrase |
| `ssh vps-root` | `100.67.100.125` (Tailscale) | Root access via Tailscale |
| `ssh vps-public` | `72.62.158.189` (public IP) | Emergency fallback only — port 22 blocked by UFW |

---

## Next steps

**Infrastructure**
- [ ] Reboot VPS to apply pending kernel upgrade
- [x] Deploy OpenClaw as `docker-compose.yml` under `server/openclaw/`, bound to Tailscale IP
- [ ] Document `relaxedon.boats` container setup under `server/`
- [ ] Set up reverse proxy (Caddy or Traefik) to manage all web services centrally

**OpenClaw / assistant**
- [x] Bind OpenClaw dashboard to Tailscale only (`tailscale serve` HTTPS, host networking)
- [x] Connect Telegram to OpenClaw (`@almiho_bot` — working)
- [ ] Connect WhatsApp (skipped for now — requires phone linking)
- [ ] Set up morning brief (Phase 2 — Google Calendar + Gmail → Telegram)

**Security**
- [x] Update `server/system/verify.sh` to include Tailscale status check
- [ ] Remove `vps-public` SSH alias once no longer needed as fallback
