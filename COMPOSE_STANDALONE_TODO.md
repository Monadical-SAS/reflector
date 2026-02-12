# Standalone Compose: Remaining Production Work

## Server/worker/beat: remove host network mode + bind mounts

Currently `server` uses `network_mode: host` and all three services bind-mount `./server/:/app/`. For full standalone prod:

- Remove `network_mode: host` from server
- Remove bind-mount volumes from server, worker, beat (use built image only)
- Update `compose_cmd` in `setup-standalone.sh` to not rely on host network
- Change `SERVER_API_URL` from `http://host.docker.internal:1250` to `http://server:1250` (server reachable via Docker network once off host mode)
