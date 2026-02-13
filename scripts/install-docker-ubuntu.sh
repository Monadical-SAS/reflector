#!/usr/bin/env bash
#
# Install Docker Engine + Compose plugin on Ubuntu.
# Ubuntu's default repos don't include docker-compose-plugin, so we add Docker's official repo.
#
# Usage:
#   ./scripts/install-docker-ubuntu.sh
#
# Requires: root or sudo
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}==>${NC} $*"; }
ok()    { echo -e "${GREEN}  ✓${NC} $*"; }
warn()  { echo -e "${YELLOW}  !${NC} $*"; }
err()   { echo -e "${RED}  ✗${NC} $*" >&2; }

# Use sudo if available and not root; otherwise run directly
if [[ $(id -u) -eq 0 ]]; then
    MAYBE_SUDO=""
elif command -v sudo &>/dev/null; then
    MAYBE_SUDO="sudo "
else
    err "Need root. Run as root or install sudo: apt install sudo"
    exit 1
fi

# Check Ubuntu
if [[ ! -f /etc/os-release ]]; then
    err "Cannot detect OS. This script is for Ubuntu."
    exit 1
fi
source /etc/os-release
if [[ "${ID:-}" != "ubuntu" ]] && [[ "${ID_LIKE:-}" != *"ubuntu"* ]]; then
    err "This script is for Ubuntu. Detected: ${ID:-unknown}"
    exit 1
fi

info "Adding Docker's official repository..."
${MAYBE_SUDO}apt update
${MAYBE_SUDO}apt install -y ca-certificates curl
${MAYBE_SUDO}install -m 0755 -d /etc/apt/keyrings
${MAYBE_SUDO}rm -f /etc/apt/sources.list.d/docker.list /etc/apt/sources.list.d/docker.sources
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | ${MAYBE_SUDO}tee /etc/apt/keyrings/docker.asc > /dev/null
${MAYBE_SUDO}chmod a+r /etc/apt/keyrings/docker.asc
CODENAME="$(. /etc/os-release && echo "${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}")"
[[ -z "$CODENAME" ]] && { err "Could not detect Ubuntu version codename."; exit 1; }
${MAYBE_SUDO}tee /etc/apt/sources.list.d/docker.sources > /dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${CODENAME}
Components: stable
Signed-By: /etc/apt/keyrings/docker.asc
EOF

info "Installing Docker Engine and Compose plugin..."
${MAYBE_SUDO}apt update
${MAYBE_SUDO}apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

if [[ -d /run/systemd/system ]]; then
    info "Enabling and starting Docker..."
    ${MAYBE_SUDO}systemctl enable --now docker
else
    err "No systemd. This script requires Ubuntu with systemd (e.g. DigitalOcean droplet)."
    exit 1
fi

DOCKER_USER="${SUDO_USER:-${USER:-root}}"
if [[ "$DOCKER_USER" != "root" ]]; then
    info "Adding $DOCKER_USER to docker group..."
    ${MAYBE_SUDO}usermod -aG docker "$DOCKER_USER"
fi

ok "Docker installed successfully."
echo ""
echo "  Log out and back in (or run: newgrp docker) so the group change takes effect."
echo "  Then verify with: docker compose version"
echo ""
