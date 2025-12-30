---
sidebar_position: 5
title: Self-Hosted GPU Setup
---

# Self-Hosted GPU Setup

This guide covers deploying Reflector's GPU processing on your own server instead of Modal.com. For the complete deployment guide, see [Deployment Guide](./overview).

## When to Use Self-Hosted GPU

**Choose self-hosted GPU if you:**
- Have GPU hardware available (NVIDIA required)
- Want full control over processing
- Prefer fixed infrastructure costs over pay-per-use
- Have privacy or data locality requirements
- Need to process audio without external API calls

**Choose Modal.com instead if you:**
- Don't have GPU hardware
- Want zero infrastructure management
- Prefer pay-per-use pricing
- Need instant scaling for variable workloads

See [Modal.com Setup](./modal-setup) for cloud GPU deployment.

## What Gets Deployed

The self-hosted GPU service provides the same API endpoints as Modal:
- `POST /v1/audio/transcriptions` - Whisper transcription
- `POST /v1/audio/transcriptions-from-url` - Transcribe from URL
- `POST /diarize` - Pyannote speaker diarization
- `POST /translate` - Audio translation

Your main Reflector server connects to this service exactly like it connects to Modal - only the URL changes.

## Prerequisites

### Hardware
- **GPU**: NVIDIA GPU with 8GB+ VRAM (tested on Tesla T4 with 15GB)
- **CPU**: 4+ cores recommended
- **RAM**: 8GB minimum, 16GB recommended
- **Disk**: 40-50GB minimum

### Software
- Public IP address
- Domain name with DNS A record pointing to server

### Accounts
- **HuggingFace account** with accepted Pyannote licenses:
  - https://huggingface.co/pyannote/speaker-diarization-3.1
  - https://huggingface.co/pyannote/segmentation-3.0
- **HuggingFace access token** from https://huggingface.co/settings/tokens

## Docker Deployment

### Step 1: Install NVIDIA Driver

```bash
sudo apt update
sudo apt install -y nvidia-driver-535
sudo reboot

# After reboot, verify installation
nvidia-smi
```

Expected output: GPU details with driver version and CUDA version.

### Step 2: Install Docker

Follow the [official Docker installation guide](https://docs.docker.com/engine/install/ubuntu/) for your distribution.

After installation, add your user to the docker group:

```bash
sudo usermod -aG docker $USER

# Log out and back in for group changes
exit
# SSH back in
```

### Step 3: Install NVIDIA Container Toolkit

```bash
# Add NVIDIA repository and install toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### Step 4: Clone Repository and Configure

```bash
git clone https://github.com/monadical-sas/reflector.git
cd reflector/gpu/self_hosted

# Create environment file
cat > .env << EOF
REFLECTOR_GPU_APIKEY=$(openssl rand -hex 16)
HF_TOKEN=your_huggingface_token_here
EOF

# Note the generated API key - you'll need it for main server config
cat .env
```

### Step 5: Build and Start

The repository includes a `compose.yml` file. Build and start:


```bash
# Build image (takes ~5 minutes, downloads ~10GB)
sudo docker compose build

# Start service
sudo docker compose up -d

# Wait for startup and verify
sleep 30
sudo docker compose logs
```

Look for: `INFO: Application startup complete. Uvicorn running on http://0.0.0.0:8000`

### Step 7: Verify GPU Access

```bash
# Check GPU is accessible from container
sudo docker exec $(sudo docker ps -q) nvidia-smi
```

Should show GPU with ~3GB VRAM used (models loaded).

---

## Configure HTTPS with Caddy

Caddy handles SSL automatically.

### Install Caddy

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl

curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | \
  sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg

curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | \
  sudo tee /etc/apt/sources.list.d/caddy-stable.list

sudo apt update
sudo apt install -y caddy
```

### Configure Reverse Proxy

Edit the Caddyfile with your domain:

```bash
sudo nano /etc/caddy/Caddyfile
```

Add (replace `gpu.example.com` with your domain):

```
gpu.example.com {
    reverse_proxy localhost:8000
}
```

Reload Caddy (auto-provisions SSL certificate):

```bash
sudo systemctl reload caddy
```

### Verify HTTPS

```bash
curl -I https://gpu.example.com/docs
# Should return HTTP/2 200
```

---

## Configure Main Reflector Server

On your main Reflector server, update `server/.env`:

```env
# GPU Processing - Self-hosted
TRANSCRIPT_BACKEND=modal
TRANSCRIPT_URL=https://gpu.example.com
TRANSCRIPT_MODAL_API_KEY=<your-generated-api-key>

DIARIZATION_BACKEND=modal
DIARIZATION_URL=https://gpu.example.com
DIARIZATION_MODAL_API_KEY=<your-generated-api-key>
```

**Note:** The backend type is `modal` because the self-hosted GPU service implements the same API contract as Modal.com. This allows you to switch between cloud and self-hosted GPU processing by only changing the URL and API key.

Restart services to apply:

```bash
docker compose -f docker-compose.prod.yml restart server worker
```

---

## Service Management

All commands in this section assume you're in `~/reflector/gpu/self_hosted/`.

```bash
# View logs
sudo docker compose logs -f

# Restart service
sudo docker compose restart

# Stop service
sudo docker compose down

# Check status
sudo docker compose ps
```

### Monitor GPU

```bash
# Check GPU usage
nvidia-smi

# Watch in real-time
watch -n 1 nvidia-smi
```

**Typical GPU memory usage:**
- Idle (models loaded): ~3GB VRAM
- During transcription: ~4-5GB VRAM

---

## Troubleshooting

### nvidia-smi fails after driver install

```bash
# Manually load kernel modules
sudo modprobe nvidia
nvidia-smi
```

### Service fails with "Could not download pyannote pipeline"

1. Verify HF_TOKEN is valid: `echo $HF_TOKEN`
2. Check model access at https://huggingface.co/pyannote/speaker-diarization-3.1
3. Update .env with correct token
4. Restart service: `sudo docker compose restart`

### Cannot connect to HTTPS endpoint

1. Verify DNS resolves: `dig +short gpu.example.com`
2. Check firewall: `sudo ufw status` (ports 80, 443 must be open)
3. Check Caddy: `sudo systemctl status caddy`
4. View Caddy logs: `sudo journalctl -u caddy -n 50`

### SSL certificate not provisioning

Requirements for Let's Encrypt:
- Ports 80 and 443 publicly accessible
- DNS resolves to server's public IP
- Valid domain (not localhost or private IP)

### Docker container won't start

```bash
# Check logs
sudo docker compose logs

# Common issues:
# - Port 8000 already in use
# - GPU not accessible (nvidia-ctk not configured)
# - Missing .env file
```

---

## Updating

```bash
cd ~/reflector/gpu/self_hosted
git pull
sudo docker compose build
sudo docker compose up -d
```
