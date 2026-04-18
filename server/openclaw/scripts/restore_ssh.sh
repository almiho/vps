#!/bin/bash
# Restore SSH keys after container restart/update
# Called by heartbeat automatically
#
# Keys live at /home/node/.openclaw/config/ssh/ — outside git, intentionally.
# On a fresh VPS: generate a new key pair there, add the public key to GitHub.
#   ssh-keygen -t ed25519 -C "alexi@openclaw-vps" -f /home/node/.openclaw/config/ssh/github -N ""

KEY_SRC="/home/node/.openclaw/config/ssh/github"

if [ ! -f "$HOME/.ssh/github" ]; then
    mkdir -p "$HOME/.ssh"
    chmod 700 "$HOME/.ssh"
    cp "$KEY_SRC" "$HOME/.ssh/github"
    cp "${KEY_SRC}.pub" "$HOME/.ssh/github.pub"
    chmod 600 "$HOME/.ssh/github"
    cat > "$HOME/.ssh/config" << 'EOF'
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/github
EOF
    ssh-keyscan github.com >> "$HOME/.ssh/known_hosts" 2>/dev/null
    echo "SSH keys restored from workspace"
else
    echo "SSH keys already present"
fi

# Restore git identity (wiped by container updates)
git config --global user.email "alexi@openclaw-vps" 2>/dev/null
git config --global user.name "AlexI" 2>/dev/null

# Ensure Claude CLI is in PATH
export PATH="/home/node/.local/bin:$PATH"
echo 'export PATH="/home/node/.local/bin:$PATH"' >> ~/.bashrc 2>/dev/null || true
