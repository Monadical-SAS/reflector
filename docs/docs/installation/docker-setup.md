---
sidebar_position: 3
title: Docker Deployment
---

# Docker Deployment

See the [Docker directory](https://github.com/monadical-sas/reflector/tree/main/docker) in the repository for the complete Docker deployment configuration.

## Quick Start

1. Clone the repository
2. Navigate to `/docker` directory
3. Copy `.env.example` to `.env`
4. Configure environment variables
5. Run `docker compose up -d`

## Configuration

Check the repository for:
- `docker-compose.yml` - Service definitions
- `.env.example` - Environment variables
- `Caddyfile` - Reverse proxy configuration
