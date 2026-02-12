# Standalone Compose: Remaining Production Work

## Server/worker/beat: remove host network mode + bind mounts

Currently `server` uses `network_mode: host` and all three services bind-mount `./server/:/app/` in the base `docker-compose.yml`. All overrides below go in `docker-compose.standalone.yml` only — do not modify the base file.

- Override `network_mode` for server (remove host mode)
- Override volumes for server, worker, beat with `!reset []` (use built image only)
- Update `compose_cmd` in `setup-standalone.sh` to not rely on host network
- Change `SERVER_API_URL` from `http://host.docker.internal:1250` to `http://server:1250` (server reachable via Docker network once off host mode)
