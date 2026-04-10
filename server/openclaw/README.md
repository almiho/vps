# server/openclaw

OpenClaw personal AI assistant, running as a Docker container on the VPS.
Accessible only via Tailscale — not reachable from the public internet.

## First-time deploy

### 1. Copy files to the VPS

From your Mac (in the repo root):

```bash
ssh vps 'mkdir -p /home/alex/apps/openclaw/{config,workspace}'
scp server/openclaw/docker-compose.yml vps:/home/alex/apps/openclaw/
scp server/openclaw/.env.example vps:/home/alex/apps/openclaw/.env
```

### 2. Pull the image

```bash
ssh vps 'docker pull ghcr.io/openclaw/openclaw:latest'
```

### 3. Run onboarding (interactive — SSH in first)

```bash
ssh vps
cd /home/alex/apps/openclaw
docker compose run --rm --no-deps --entrypoint node openclaw-gateway \
  dist/index.js onboard --mode local --no-install-daemon
```

Onboarding will:
- Prompt for your AI provider API key (Anthropic recommended)
- Generate a gateway token and write it to the config dir

After onboarding, copy the generated token into `.env`:

```bash
grep OPENCLAW_GATEWAY_TOKEN config/openclaw/.env   # find the token
# then paste it into /home/alex/apps/openclaw/.env
```

### 4. Start the gateway

```bash
cd /home/alex/apps/openclaw
docker compose up -d openclaw-gateway
```

### 5. Verify it's running

```bash
docker compose ps
curl -fsS http://100.67.100.125:18789/healthz
```

### 6. Open the dashboard (from your Mac via Tailscale)

```
http://100.67.100.125:18789
```

### 7. Connect WhatsApp

```bash
ssh vps
cd /home/alex/apps/openclaw
docker compose run --rm openclaw-cli channels login
```

Scan the QR code with WhatsApp on your phone.

---

## Day-to-day management

| Task | Command |
|---|---|
| Start | `docker compose up -d openclaw-gateway` |
| Stop | `docker compose down` |
| Restart | `docker compose restart openclaw-gateway` |
| Logs | `docker compose logs -f openclaw-gateway` |
| Update image | `docker compose pull && docker compose up -d` |

All commands run from `/home/alex/apps/openclaw/` on the VPS.

---

## Security notes

- The gateway is bound to `100.67.100.125:18789` (Tailscale IP) — not publicly reachable.
- The gateway token in `.env` is a password — rotate it if exposed.
- API keys in `.env` are never committed to the repo (`.env` is gitignored).
