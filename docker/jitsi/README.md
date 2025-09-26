# Local Jitsi Setup with Recording

This directory contains a complete local Jitsi Meet setup with automatic recording capabilities and event collection.

## Quick Start

### Prerequisites

1. **Docker** and **Docker Compose** installed
2. **Node.js** and **npm** for event collector
3. **mkcert** for SSL certificates (install with `brew install mkcert`)
4. **Add to /etc/hosts:**
   ```bash
   echo "127.0.0.1 jitsi.local" | sudo tee -a /etc/hosts
   ```

### Setup SSL Certificates

```bash
cd ssl
mkcert jitsi.local localhost 127.0.0.1 ::1
cp jitsi.local+3.pem jitsi.crt
cp jitsi.local+3-key.pem jitsi.key
```

### Start Services

```bash
# Start all Jitsi services (includes event collector)
docker compose -f docker-compose.simple.yml up -d
```

**All services start automatically including:**
- Jitsi stack (nginx, web, prosody, jicofo, jvb, jibri)
- Redis database
- Event collector (containerized)

### Verify Services Running

```bash
docker ps --filter name=jitsi
```

You should see:
- `jitsi_nginx` (ports 80, 443)
- `jitsi_web`
- `jitsi_prosody`
- `jitsi_jicofo`
- `jitsi_jvb` (ports 4443, 10000)
- `jitsi_jibri` (recording service)
- `jitsi_redis` (port 6380)
- `jitsi_event_collector` (port 3002)

## Testing

### Test Jitsi Meeting

1. **Start Frontend** (if not already running):
   ```bash
   cd ../../www
   pnpm dev
   ```

2. **Open Test Page:**
   - Navigate to: `http://localhost:3000/jitsi-test?local=true`
   - Fill form:
     - Room: `my-test-room`
     - Name: `Your Name`
   - Click "Join Meeting"

3. **Verify Features:**
   - ✅ Meeting loads in iframe
   - ✅ Auto-recording starts (console: "🎬 Attempting to start recording...")
   - ✅ No "recording failed to start" errors
   - ✅ Recording indicator shows "Recording" in UI

### Verify Recording Files

**After leaving meeting:**
```bash
# Check recording files created
ls -la recordings/

# View specific recording
ls -la recordings/*/
```

**Files created:**
- `{room-name}_{timestamp}.mp4` - Recording file
- `metadata.json` - Recording metadata

### Verify Events in Redis

```bash
# Check events for specific room
redis-cli -p 6380 LRANGE "jitsi:events:my-test-room" 0 -1

# Monitor events in real-time
redis-cli -p 6380 MONITOR

# Subscribe to event publications
redis-cli -p 6380 PSUBSCRIBE "jitsi:*"
```

**Expected events:**
- `api_ready` - Meeting API initialized
- `videoConferenceJoined` - Participant joined
- `recording_status_changed` - Recording started/stopped
- `videoConferenceLeft` - Participant left
- `ready_to_close` - Meeting ended

## Architecture

```
Frontend (localhost:3000)
    ↓ HTTPS iframe + Client events
Nginx Proxy (jitsi.local:443)
    ↓ SSL termination
Jitsi Web + Prosody + Jicofo + JVB
    ↓ Recording requests
Jibri → MP4 files (/recordings/)
    ↓ Webhook events + Finalize script
Event Collector (localhost:3002)
    ↓ Publish/Store
Redis (localhost:6380)
```

### Event Flow

1. **Client Events** (from frontend):
   - `videoConferenceJoined` - User joins with participant info
   - `videoConferenceLeft` - User leaves meeting
   - `recording_status_changed` - Recording state changes

2. **Jibri Events** (from recording service):
   - `recording_completed` - Recording finished with file metadata
   - `recording_available` - Recording file ready for processing
   - `recording_failed` - Recording error occurred

3. **Event Correlation**:
   - Events linked by `roomName` and `sessionId`
   - Recording files contain session ID in path
   - Participant data from client events enriches recording metadata

## Configuration

### Key Environment Variables

**Jibri (Recording Service):**
- `JIBRI_WEBHOOK_SUBSCRIBERS` - Webhook endpoint for events (http://event-collector:3002/webhook/jibri)
- `JIBRI_FINALIZE_RECORDING_SCRIPT_PATH` - Post-recording script (/scripts/finalize.sh)
- `JIBRI_RECORDING_DIR` - Recording output directory (/recordings)

**Event Collector:**
- `REDIS_URL` - Redis connection (default: redis://localhost:6380)
- `ENABLE_EVENT_LOGGING` - Enable detailed logging (true/false)
- `REFLECTOR_WEBHOOK_URL` - Forward events to Reflector (optional)

**Frontend:**
- `NEXT_PUBLIC_JITSI_DOMAIN` - Jitsi domain (default: jitsi.local)
- `NEXT_PUBLIC_EVENT_COLLECTOR_URL` - Event collector URL (default: localhost:3002)
- `NEXT_PUBLIC_USE_LOCAL_JITSI` - Force local Jitsi (true/false)

### Important Files

- `docker-compose.simple.yml` - Self-contained Jitsi stack
- `docker-compose.yml` - Production version (requires external network)
- `nginx.conf` - SSL proxy configuration
- `event-collector/` - TypeScript event aggregation service
- `.gitignore` - Excludes recordings and certificates

## Troubleshooting

### Common Issues

**Recording fails to start:**
- Check Jibri container logs: `docker logs jitsi_jibri`
- Verify DNS mapping in container: `docker exec jitsi_jibri cat /etc/hosts`
- Should see: `192.168.x.x jitsi.local`

**SSL certificate errors:**
- Verify mkcert certificates exist: `ls -la ssl/`
- Trust certificates: Run mkcert commands from setup section

**Event collector not receiving events:**
- Check event collector logs for incoming webhook calls
- Verify frontend can reach localhost:3002
- Check Redis connection: `redis-cli -p 6380 ping`

**iframe embedding blocked:**
- Check nginx Content-Security-Policy headers
- Verify frontend loads from localhost:3000

### Logs and Debugging

```bash
# Jitsi container logs
docker logs jitsi_jibri    # Recording service
docker logs jitsi_prosody  # XMPP server
docker logs jitsi_nginx    # SSL proxy

# Event collector logs
# See running event collector terminal

# Redis operations
redis-cli -p 6380 MONITOR
```

### Clean Restart

```bash
# Stop all services
docker compose -f docker-compose.simple.yml down

# Remove volumes (clears config)
docker compose -f docker-compose.simple.yml down -v

# Clean start
docker compose -f docker-compose.simple.yml up -d
```

## Production Deployment

For production use:
1. Use `docker-compose.yml` (not simple version)
2. Configure external `reflector` network
3. Set proper environment variables in `.env`
4. Use real SSL certificates (not mkcert)
5. Configure `REFLECTOR_WEBHOOK_URL` for database integration

## Security Notes

- Local setup uses self-signed certificates (mkcert)
- No authentication enabled (ENABLE_AUTH=0)
- Recording files are stored locally in `./recordings/`
- Event collector has no authentication
- Redis has no password protection

**For production, enable proper authentication and security measures.**