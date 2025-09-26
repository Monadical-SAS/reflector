# Jitsi Local Setup - Testing Instructions

## Current Status

✅ **Completed:**
1. Created Docker Compose configuration for local Jitsi with Jibri
2. Built event-collector service (TypeScript/Express)
3. Modified frontend to support local Jitsi
4. Event collector is running on port 3002
5. Docker containers are started (but Docker commands are hanging)

## Services Running

| Service | Port | Status |
|---------|------|--------|
| Jitsi Web | 8080 | Started (Docker hanging) |
| Jitsi Web HTTPS | 8443 | Started (Docker hanging) |
| JVB (Video Bridge) | 10000/udp, 4443/tcp | Started |
| Redis | 6380 | Started |
| Event Collector | 3002 | ✅ Running |
| Frontend | 3000 | ✅ Running |

## Testing Steps

### 1. Verify Docker is Working
```bash
# Check Docker Desktop is running
docker ps

# If Docker commands hang, restart Docker Desktop
```

### 2. Check Jitsi Services
```bash
cd /Users/firfi/work/clients/monadical/reflector/docker/jitsi

# Check container status
docker-compose -f docker-compose.simple.yml ps

# View logs if needed
docker-compose -f docker-compose.simple.yml logs -f
```

### 3. Test Event Collector
```bash
# Health check (should return {"status":"ok"})
curl http://localhost:3002/health

# View collected events
curl http://localhost:3002/events
```

### 4. Test Frontend Integration

1. Open browser to: http://localhost:3000/jitsi-test?local=true
2. Fill in the form:
   - Room Name: test-room
   - Display Name: Test User
   - Click "Join Meeting"
3. The page should connect to local Jitsi at localhost:8080

### 5. Monitor Events

Watch event collector logs to see events flowing:
```bash
# In the terminal where event-collector is running, you should see:
# 📥 Client events
# 📡 Publishing events
```

### 6. Test Recording (Once Jibri is Working)

1. In the meeting, click the "Record" button
2. Check event collector logs for recording events
3. Recording files will be saved to: `/recordings/` in the Jibri container

## Troubleshooting

### Docker Issues
If Docker commands hang:
1. Quit Docker Desktop completely
2. Restart Docker Desktop
3. Wait for it to fully start
4. Try commands again

### Port Conflicts
If ports are already in use:
```bash
# Check what's using a port
lsof -i :8080

# Stop conflicting service or change port in docker-compose.simple.yml
```

### Event Collector Not Working
```bash
# Restart event collector
cd /Users/firfi/work/clients/monadical/reflector/docker/jitsi/event-collector
npm run build && REDIS_URL=redis://localhost:6380 ENABLE_EVENT_LOGGING=true npm start
```

## Next Steps

Once Docker is working properly:

1. **Verify Recording**: Test that Jibri can record meetings
2. **Backend Integration**: Create Jitsi webhook endpoints in Reflector backend
3. **Event Processing**: Implement recording upload to S3
4. **Migration**: Create migration path from Whereby to Jitsi

## Architecture Overview

```
Browser → Jitsi Test Page → LocalJitsiMeetSDK
              ↓
    Local Jitsi (localhost:8080)
              ↓
    Prosody + Jicofo + JVB
              ↓
        Jibri (Recording)
              ↓
       Event Collector
              ↓
     Redis Pub/Sub → Reflector Backend
```

## Files Created/Modified

- `/docker/jitsi/docker-compose.simple.yml` - Jitsi stack configuration
- `/docker/jitsi/event-collector/` - Event aggregation service
- `/www/app/(app)/jitsi-test/components/LocalJitsiMeetSDK.tsx` - Local Jitsi component
- `/www/app/(app)/jitsi-test/page.tsx` - Modified to support ?local=true parameter