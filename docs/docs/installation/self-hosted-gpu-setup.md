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
- `POST /diarize` - Pyannote speaker diarization

Your main Reflector server connects to this service exactly like it connects to Modal - only the URL changes.

## Prerequisites

### Hardware
- **GPU**: NVIDIA GPU with 8GB+ VRAM (tested on Tesla T4 with 15GB)
- **CPU**: 4+ cores recommended
- **RAM**: 8GB minimum, 16GB recommended
- **Disk**:
  - Docker method: 40-50GB minimum
  - Systemd method: 25-30GB minimum

### Software
- Ubuntu 22.04 or 24.04
- Public IP address
- Domain name with DNS A record pointing to server

### Accounts
- **HuggingFace account** with accepted Pyannote licenses:
  - https://huggingface.co/pyannote/speaker-diarization-3.1
  - https://huggingface.co/pyannote/segmentation-3.0
- **HuggingFace access token** from https://huggingface.co/settings/tokens

## Choose Deployment Method

### Docker Deployment (Recommended)

**Pros:**
- Container isolation and reproducibility
- No manual library path configuration
- Easier to replicate across servers
- Built-in restart policies
- Simpler dependency management

**Cons:**
- Higher disk usage (~15GB for container)
- Requires 40-50GB disk minimum

**Best for:** Teams wanting reproducible deployments, multiple GPU servers

### Systemd Deployment

**Pros:**
- Lower disk usage (~8GB total)
- Direct GPU access (no container layer)
- Works on smaller disks (25-30GB)

**Cons:**
- Manual `LD_LIBRARY_PATH` configuration
- Less portable across systems

**Best for:** Single GPU server, limited disk space

---

## Docker Deployment

### Step 1: Install NVIDIA Driver

```bash
sudo apt update
sudo apt install -y nvidia-driver-535

# Load kernel modules
sudo modprobe nvidia

# Verify installation
nvidia-smi
```

Expected output: GPU details with driver version and CUDA version.

### Step 2: Install Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# Log out and back in for group changes
exit
# SSH back in
```

### Step 3: Install NVIDIA Container Toolkit

```bash
# Add NVIDIA repository
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Install toolkit
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Configure Docker runtime
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

### Step 5: Create Docker Compose File

```bash
cat > compose.yml << 'EOF'
services:
  reflector_gpu:
    build:
      context: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./cache:/root/.cache
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    restart: unless-stopped
EOF
```

### Step 6: Build and Start

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

## Systemd Deployment

### Step 1: Install NVIDIA Driver

```bash
sudo apt update
sudo apt install -y nvidia-driver-535

# Load kernel modules
sudo modprobe nvidia

# Verify installation
nvidia-smi
```

### Step 2: Install Dependencies

```bash
# Install ffmpeg
sudo apt install -y ffmpeg

# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.local/bin/env

# Clone repository
git clone https://github.com/monadical-sas/reflector.git
cd reflector/gpu/self_hosted
```

### Step 3: Configure Environment

```bash
# Create environment file
cat > .env << EOF
REFLECTOR_GPU_APIKEY=$(openssl rand -hex 16)
HF_TOKEN=your_huggingface_token_here
EOF

# Note the generated API key
cat .env
```

### Step 4: Install Python Packages

```bash
# Install dependencies (~3GB download)
uv sync
```

### Step 5: Create Systemd Service

```bash
# Generate library paths for NVIDIA packages
export NVIDIA_LIBS=$(find ~/reflector/gpu/self_hosted/.venv/lib/python3.12/site-packages/nvidia -name lib -type d | tr '\n' ':')

# Load environment variables
source ~/reflector/gpu/self_hosted/.env

# Create service file
sudo tee /etc/systemd/system/reflector-gpu.service << EOFSVC
[Unit]
Description=Reflector GPU Service (Transcription & Diarization)
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/reflector/gpu/self_hosted
Environment="PATH=$HOME/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="HF_TOKEN=${HF_TOKEN}"
Environment="REFLECTOR_GPU_APIKEY=${REFLECTOR_GPU_APIKEY}"
Environment="LD_LIBRARY_PATH=${NVIDIA_LIBS}"
ExecStart=$HOME/reflector/gpu/self_hosted/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOFSVC

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable reflector-gpu
sudo systemctl start reflector-gpu
```

### Step 6: Verify Service

```bash
# Check status
sudo systemctl status reflector-gpu

# View logs
sudo journalctl -u reflector-gpu -f
```

Look for: `INFO: Application startup complete.`

---

## Configure HTTPS with Caddy

Both deployment methods need HTTPS for production. Caddy handles SSL automatically.

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

```bash
sudo tee /etc/caddy/Caddyfile << 'EOF'
gpu.example.com {
    reverse_proxy localhost:8000
}
EOF

# Reload Caddy (auto-provisions SSL certificate)
sudo systemctl reload caddy
```

Replace `gpu.example.com` with your domain.

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

### Docker

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

### Systemd

```bash
# View logs
sudo journalctl -u reflector-gpu -f

# Restart service
sudo systemctl restart reflector-gpu

# Stop service
sudo systemctl stop reflector-gpu

# Check status
sudo systemctl status reflector-gpu
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

## Performance Notes

**Tesla T4 benchmarks:**
- Transcription: ~2-3x real-time (10 min audio in 3-5 min)
- Diarization: ~1.5x real-time
- Max concurrent requests: 2-3 (depends on audio length)
- First request warmup: ~10 seconds (model loading)

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
3. Regenerate service/compose with correct token
4. Restart service

### cuDNN library loading errors (Systemd only)

Symptom: `Unable to load libcudnn_cnn.so`

Regenerate the systemd service file - the `LD_LIBRARY_PATH` must include all NVIDIA package directories.

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

## Security Considerations

1. **API Key**: Keep `REFLECTOR_GPU_APIKEY` secret, rotate periodically
2. **HuggingFace Token**: Treat as password, never commit to git
3. **Firewall**: Only expose ports 80 and 443 publicly
4. **Updates**: Regularly update system packages
5. **Monitoring**: Set up alerts for service failures

---

## Updating

### Docker

```bash
cd ~/reflector/gpu/self_hosted
git pull
sudo docker compose build
sudo docker compose up -d
```

### Systemd

```bash
cd ~/reflector/gpu/self_hosted
git pull
uv sync
sudo systemctl restart reflector-gpu
```
