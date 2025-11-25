---
sidebar_position: 1
title: Installation Overview
---

# Installation Overview

Reflector is designed for self-hosted deployment, giving you complete control over your infrastructure and data.

## Deployment Options

### Docker Deployment (Recommended)

The easiest way to deploy Reflector:
- Pre-configured containers
- Automated dependency management
- Consistent environment
- Easy updates

### Manual Installation

For custom deployments:
- Greater control over configuration
- Integration with existing infrastructure
- Custom optimization options
- Development environments

## Requirements

### System Requirements

**Minimum Requirements:**
- CPU: 4 cores
- RAM: 8 GB
- Storage: 50 GB
- OS: Ubuntu 20.04+ or similar Linux

**Recommended Requirements:**
- CPU: 8+ cores
- RAM: 16 GB
- Storage: 100 GB SSD
- GPU: NVIDIA GPU with 8GB+ VRAM (for local processing)

### Network Requirements

- Public IP address (for WebRTC)
- Ports: 80, 443, 8000, 3000
- Domain name (for SSL)
- SSL certificate (Let's Encrypt supported)

## Required Services

### Core Services

These services are required for basic operation:

1. **PostgreSQL** - Primary database
2. **Redis** - Message broker and cache
3. **Docker** - Container runtime

### GPU Processing

Choose one:
- **Modal.com** - Serverless GPU (recommended)
- **Local GPU** - Self-hosted GPU processing

### Optional Services

Enhance functionality with:
- **AWS S3** - Long-term storage
- **Whereby** - Video conferencing rooms
- **Authentik** - Enterprise authentication
- **Zulip** - Chat integration

## Quick Start

### Using Docker Compose

1. Clone the repository:
```bash
git clone https://github.com/monadical-sas/reflector.git
cd reflector
```

2. Navigate to docker directory:
```bash
cd docker
```

3. Copy and configure environment:
```bash
cp .env.example .env
# Edit .env with your settings
```

4. Start services:
```bash
docker compose up -d
```

5. Access Reflector:
- Frontend: https://your-domain.com
- API: https://your-domain.com/api

## Configuration Overview

### Essential Configuration

```env
# Database
DATABASE_URL=postgresql://user:pass@localhost/reflector

# Redis
REDIS_URL=redis://localhost:6379

# Modal.com (for GPU processing)
TRANSCRIPT_MODAL_API_KEY=your-key
DIARIZATION_MODAL_API_KEY=your-key

# Domain
DOMAIN=your-domain.com
```

### Security Configuration

```env
# Authentication
REFLECTOR_AUTH_BACKEND=jwt
NEXTAUTH_SECRET=generate-strong-secret

# SSL (handled by Caddy)
# Automatic with Let's Encrypt
```

## Service Architecture

```mermaid
graph TD
    A[Caddy Reverse Proxy] --> B[Frontend - Next.js]
    A --> C[Backend - FastAPI]
    C --> D[PostgreSQL]
    C --> E[Redis]
    C --> F[Celery Workers]
    F --> G[Modal.com GPU]
```

## Next Steps

1. **Review Requirements**: [System Requirements](./requirements)
2. **Docker Setup**: [Docker Deployment Guide](./docker-setup)
3. **Configure Services**:
   - [Modal.com Setup](./modal-setup)
   - [Whereby Setup](./whereby-setup)
   - [AWS S3 Setup](./aws-setup)
4. **Optional Services**:
   - [Authentik Setup](./authentik-setup)
   - [Zulip Setup](./zulip-setup)

## Getting Help

- [GitHub Issues](https://github.com/monadical-sas/reflector/issues)
- [Community Discord](#)
