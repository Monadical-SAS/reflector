# Jitsi Meet Integration Configuration Guide

This guide explains how to configure Reflector to use your self-hosted Jitsi Meet installation for video meetings, recording, and participant tracking.

## Overview

Jitsi Meet is an open-source video conferencing platform that can be self-hosted. Reflector integrates with Jitsi Meet to:

- Create secure meeting rooms with JWT authentication
- Track participant join/leave events via Prosody webhooks
- Record meetings using Jibri recording service
- Process recordings for transcription and analysis

## Requirements

### Self-Hosted Jitsi Meet

You need a complete Jitsi Meet installation including:

1. **Jitsi Meet Web Interface** - The main meeting interface
2. **Prosody XMPP Server** - Handles room management and authentication
3. **Jicofo (JItsi COnference FOcus)** - Manages media sessions
4. **Jitsi Videobridge (JVB)** - Handles WebRTC media routing
5. **Jibri Recording Service** - Records meetings (optional but recommended)

### System Requirements

- **Domain with SSL Certificate** - Required for WebRTC functionality
- **Prosody mod_event_sync** - For webhook event handling
- **JWT Authentication** - For secure room access control
- **Storage Solution** - For recording files (local or cloud)

## Configuration Variables

Add the following environment variables to your Reflector `.env` file:

### Required Variables

```bash
# Jitsi Meet Domain (without https://)
JITSI_DOMAIN=meet.example.com

# JWT Secret for room authentication (generate with: openssl rand -hex 32)
JITSI_JWT_SECRET=your-64-character-hex-secret-here

# Webhook secret for event handling (generate with: openssl rand -hex 16)
JITSI_WEBHOOK_SECRET=your-32-character-hex-secret-here
```

### Optional Variables

```bash
# Application identifier (should match Jitsi configuration)
JITSI_APP_ID=reflector

# JWT issuer and audience (should match Jitsi configuration)
JITSI_JWT_ISSUER=reflector
JITSI_JWT_AUDIENCE=jitsi
```

## Installation Steps

### 1. Jitsi Meet Server Installation

#### Quick Installation (Ubuntu/Debian)

```bash
# Add Jitsi repository
curl -fsSL https://download.jitsi.org/jitsi-key.gpg.key | sudo gpg --dearmor -o /usr/share/keyrings/jitsi-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/jitsi-keyring.gpg] https://download.jitsi.org stable/" | sudo tee /etc/apt/sources.list.d/jitsi-stable.list

# Install Jitsi Meet
sudo apt update
sudo apt install jitsi-meet

# Configure SSL certificate
sudo /usr/share/jitsi-meet/scripts/install-letsencrypt-cert.sh
```

#### Docker Installation

```bash
# Clone Jitsi Docker repository
git clone https://github.com/jitsi/docker-jitsi-meet
cd docker-jitsi-meet

# Copy environment template
cp env.example .env

# Edit configuration
nano .env

# Start services
docker-compose up -d
```

### 2. JWT Authentication Setup

#### Update Prosody Configuration

Edit `/etc/prosody/conf.d/your-domain.cfg.lua`:

```lua
VirtualHost "meet.example.com"
    authentication = "token"
    app_id = "reflector"
    app_secret = "your-jwt-secret-here"

    -- Allow anonymous access for guests
    c2s_require_encryption = false
    admins = { "focusUser@auth.meet.example.com" }

    modules_enabled = {
        "bosh";
        "pubsub";
        "ping";
        "roster";
        "saslauth";
        "tls";
        "dialback";
        "disco";
        "carbons";
        "pep";
        "private";
        "blocklist";
        "vcard";
        "version";
        "uptime";
        "time";
        "ping";
        "register";
        "admin_adhoc";
        "token_verification";
        "event_sync";  -- Required for webhooks
    }
```

#### Configure Jitsi Meet Interface

Edit `/etc/jitsi/meet/your-domain-config.js`:

```javascript
var config = {
    hosts: {
        domain: 'meet.example.com',
        muc: 'conference.meet.example.com'
    },

    // Enable JWT authentication
    enableUserRolesBasedOnToken: true,

    // Recording configuration
    fileRecordingsEnabled: true,
    liveStreamingEnabled: false,

    // Reflector integration settings
    prejoinPageEnabled: true,
    requireDisplayName: true
};
```

### 3. Webhook Event Configuration

#### Install Event Sync Module

```bash
# Download the module
cd /usr/share/jitsi-meet/prosody-plugins/
wget https://raw.githubusercontent.com/jitsi-contrib/prosody-plugins/main/mod_event_sync.lua
```

#### Configure Event Sync

Add to your Prosody configuration:

```lua
Component "conference.meet.example.com" "muc"
    storage = "memory"
    modules_enabled = {
        "muc_meeting_id";
        "muc_domain_mapper";
        "polls";
        "event_sync";  -- Enable event sync
    }

    -- Event sync webhook configuration
    event_sync_url = "https://your-reflector-domain.com/v1/jitsi/events"
    event_sync_secret = "your-webhook-secret-here"

    -- Events to track
    event_sync_events = {
        "muc-occupant-joined",
        "muc-occupant-left",
        "jibri-recording-on",
        "jibri-recording-off"
    }

#### Webhook Event Payload Examples

**Participant Joined Event:**
```json
{
  "event": "muc-occupant-joined",
  "room": "reflector-my-room-uuid123",
  "timestamp": "2025-01-15T10:30:00.000Z",
  "data": {
    "occupant_id": "participant-456",
    "nick": "John Doe",
    "role": "participant",
    "affiliation": "none"
  }
}
```

**Recording Started Event:**
```json
{
  "event": "jibri-recording-on",
  "room": "reflector-my-room-uuid123",
  "timestamp": "2025-01-15T10:32:00.000Z",
  "data": {
    "recording_id": "rec-789",
    "initiator": "moderator-123"
  }
}
```

**Recording Completed Event:**
```json
{
  "room_name": "reflector-my-room-uuid123",
  "recording_file": "/var/recordings/rec-789.mp4",
  "recording_status": "completed",
  "timestamp": "2025-01-15T11:15:00.000Z"
}
```

### 4. Jibri Recording Setup (Optional)

#### Install Jibri

```bash
# Install Jibri package
sudo apt install jibri

# Create recording directory
sudo mkdir -p /var/recordings
sudo chown jibri:jibri /var/recordings
```

#### Configure Jibri

Edit `/etc/jitsi/jibri/jibri.conf`:

```hocon
jibri {
    recording {
        recordings-directory = "/var/recordings"
        finalize-script = "/opt/jitsi/jibri/finalize.sh"
    }

    api {
        xmpp {
            environments = [{
                name = "prod environment"
                xmpp-server-hosts = ["meet.example.com"]
                xmpp-domain = "meet.example.com"

                control-muc {
                    domain = "internal.auth.meet.example.com"
                    room-name = "JibriBrewery"
                    nickname = "jibri-nickname"
                }

                control-login {
                    domain = "auth.meet.example.com"
                    username = "jibri"
                    password = "jibri-password"
                }
            }]
        }
    }
}
```

#### Create Finalize Script

Create `/opt/jitsi/jibri/finalize.sh`:

```bash
#!/bin/bash
# Jibri finalize script for Reflector integration

RECORDING_FILE="$1"
ROOM_NAME="$2"
REFLECTOR_API_URL="${REFLECTOR_API_URL:-http://localhost:1250}"

# Prepare webhook payload
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)
PAYLOAD=$(cat <<EOF
{
    "room_name": "$ROOM_NAME",
    "recording_file": "$RECORDING_FILE",
    "recording_status": "completed",
    "timestamp": "$TIMESTAMP"
}
EOF
)

# Generate signature
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$JITSI_WEBHOOK_SECRET" | cut -d' ' -f2)

# Send webhook to Reflector
curl -X POST "$REFLECTOR_API_URL/v1/jibri/recording-complete" \
    -H "Content-Type: application/json" \
    -H "X-Jitsi-Signature: $SIGNATURE" \
    -d "$PAYLOAD"

echo "Recording finalization webhook sent for room: $ROOM_NAME"
```

Make executable:
```bash
sudo chmod +x /opt/jitsi/jibri/finalize.sh
```

### 5. Restart Services

After configuration changes:

```bash
sudo systemctl restart prosody
sudo systemctl restart jicofo
sudo systemctl restart jitsi-videobridge2
sudo systemctl restart jibri
sudo systemctl restart nginx
```

## Room Configuration

### Creating Jitsi Rooms

Create rooms with Jitsi platform in Reflector:

```bash
curl -X POST "https://your-reflector-domain.com/v1/rooms" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "name": "my-jitsi-room",
    "platform": "jitsi",
    "recording_type": "cloud",
    "recording_trigger": "automatic-2nd-participant",
    "is_locked": false,
    "room_mode": "normal"
  }'
```

### Meeting Creation

Meetings automatically use JWT authentication:

```bash
curl -X POST "https://your-reflector-domain.com/v1/rooms/my-jitsi-room/meeting" \
  -H "Authorization: Bearer $AUTH_TOKEN"
```

Response includes JWT-authenticated URLs:
```json
{
  "id": "meeting-uuid",
  "room_name": "reflector-my-jitsi-room-123456",
  "room_url": "https://meet.example.com/room?jwt=user-token",
  "host_room_url": "https://meet.example.com/room?jwt=moderator-token"
}
```

## Features and Capabilities

### JWT Authentication

Reflector automatically generates JWT tokens with:
- **Room Access Control** - Secure room entry
- **User Roles** - Moderator vs participant permissions
- **Expiration** - Configurable token lifetime (default 8 hours)
- **Custom Claims** - Room-specific metadata

### Recording Options

**Recording Types:**
- `"none"` - No recording
- `"local"` - Local Jibri recording
- `"cloud"` - Cloud recording (requires external storage)

**Recording Triggers:**
- `"none"` - Manual recording only
- `"prompt"` - Prompt users to start
- `"automatic"` - Start immediately
- `"automatic-2nd-participant"` - Start when 2nd person joins

### Event Tracking and Storage

Reflector automatically stores all webhook events in the `meetings` table for comprehensive meeting analytics:

**Supported Event Types:**
- `muc-occupant-joined` - Participant joined the meeting
- `muc-occupant-left` - Participant left the meeting
- `jibri-recording-on` - Recording started
- `jibri-recording-off` - Recording stopped
- `recording_completed` - Recording file ready for processing

**Event Storage Structure:**
Each webhook event is stored as a JSON object in the `meetings.events` column:
```json
{
  "type": "muc-occupant-joined",
  "timestamp": "2025-01-15T10:30:00.123456Z",
  "data": {
    "timestamp": "2025-01-15T10:30:00Z",
    "user_id": "participant-123",
    "display_name": "John Doe"
  }
}
```

**Querying Stored Events:**
```sql
-- Get all events for a meeting
SELECT events FROM meeting WHERE id = 'meeting-uuid';

-- Count participant joins
SELECT json_array_length(
  json_extract(events, '$[*] ? (@.type == "muc-occupant-joined")')
) as total_joins FROM meeting WHERE id = 'meeting-uuid';
```

## Testing and Verification

### Health Check

Test Jitsi webhook integration:

```bash
curl "https://your-reflector-domain.com/v1/jitsi/health"
```

Expected response:
```json
{
    "status": "ok",
    "service": "jitsi-webhooks",
    "timestamp": "2025-01-15T10:30:00.000Z",
    "webhook_secret_configured": true
}
```

### JWT Token Testing

Verify JWT generation works:
```bash
# Create a test meeting
MEETING=$(curl -X POST "https://your-reflector-domain.com/v1/rooms/test-room/meeting" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq -r '.room_url')

echo "Test meeting URL: $MEETING"
```

### Webhook Testing

#### Manual Webhook Event Testing

Test participant join event:
```bash
# Generate proper signature
PAYLOAD='{"event":"muc-occupant-joined","room":"reflector-test-room-uuid","timestamp":"2025-01-15T10:30:00.000Z","data":{"user_id":"test-user","display_name":"Test User"}}'
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$JITSI_WEBHOOK_SECRET" | cut -d' ' -f2)

curl -X POST "https://your-reflector-domain.com/v1/jitsi/events" \
  -H "Content-Type: application/json" \
  -H "X-Jitsi-Signature: $SIGNATURE" \
  -d "$PAYLOAD"
```

Expected response:
```json
{
  "status": "ok",
  "event": "muc-occupant-joined",
  "room": "reflector-test-room-uuid"
}
```

#### Recording Webhook Testing

Test recording completion event:
```bash
PAYLOAD='{"room_name":"reflector-test-room-uuid","recording_file":"/recordings/test.mp4","recording_status":"completed","timestamp":"2025-01-15T10:30:00.000Z"}'
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$JITSI_WEBHOOK_SECRET" | cut -d' ' -f2)

curl -X POST "https://your-reflector-domain.com/v1/jibri/recording-complete" \
  -H "Content-Type: application/json" \
  -H "X-Jitsi-Signature: $SIGNATURE" \
  -d "$PAYLOAD"
```

#### Event Storage Verification

Verify events were stored:
```bash
# Check meeting events via API (requires authentication)
curl -H "Authorization: Bearer $AUTH_TOKEN" \
  "https://your-reflector-domain.com/v1/meetings/{meeting-id}"
```

## Troubleshooting

### Common Issues

#### JWT Authentication Failures

**Symptoms**: Users cannot join rooms, "Authentication failed" errors

**Solutions**:
1. Verify `JITSI_JWT_SECRET` matches Prosody configuration
2. Check JWT token hasn't expired (default 8 hours)
3. Ensure system clocks are synchronized between servers
4. Validate JWT issuer/audience configuration matches

**Debug JWT tokens**:
```bash
# Decode JWT payload
echo "JWT_TOKEN_HERE" | cut -d'.' -f2 | base64 -d | jq
```

#### Webhook Events Not Received

**Symptoms**: Participant counts not updating, no recording events

**Solutions**:
1. Verify `mod_event_sync` is loaded in Prosody
2. Check webhook URL is accessible from Jitsi server
3. Validate webhook signature generation
4. Review Prosody and Reflector logs

**Debug webhook connectivity**:
```bash
# Test from Jitsi server
curl -v "https://your-reflector-domain.com/v1/jitsi/health"

# Check Prosody logs
sudo tail -f /var/log/prosody/prosody.log
```

#### Webhook Signature Verification Issues

**Symptoms**: HTTP 401 "Invalid webhook signature" errors

**Solutions**:
1. Verify webhook secret matches between Jitsi and Reflector
2. Check payload encoding (no extra whitespace)
3. Ensure proper HMAC-SHA256 signature generation

**Debug signature generation**:
```bash
# Test signature manually
PAYLOAD='{"event":"test","room":"test","timestamp":"2025-01-15T10:30:00.000Z","data":{}}'
SECRET="your-webhook-secret-here"

# Generate signature (should match X-Jitsi-Signature header)
echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2

# Test with curl
curl -X POST "https://your-reflector-domain.com/v1/jitsi/events" \
  -H "Content-Type: application/json" \
  -H "X-Jitsi-Signature: $(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)" \
  -d "$PAYLOAD" -v
```

#### Event Storage Problems

**Symptoms**: Events received but not stored in database

**Solutions**:
1. Check database connectivity and permissions
2. Verify meeting exists before event processing
3. Review Reflector application logs
4. Ensure JSON column support in database

**Debug event storage**:
```bash
# Check meeting exists
curl -H "Authorization: Bearer $TOKEN" \
  "https://your-reflector-domain.com/v1/meetings/{meeting-id}"

# Monitor database queries (if using PostgreSQL)
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity WHERE query LIKE '%meeting%';"

# Check Reflector logs for event processing
sudo journalctl -u reflector -f | grep -E "(event|webhook|jitsi)"
```

#### Recording Issues

**Symptoms**: Recordings not starting, finalize script errors

**Solutions**:
1. Verify Jibri service status: `sudo systemctl status jibri`
2. Check recording directory permissions: `/var/recordings`
3. Validate finalize script execution permissions
4. Monitor Jibri logs: `sudo journalctl -u jibri -f`

**Test finalize script**:
```bash
sudo -u jibri /opt/jitsi/jibri/finalize.sh "/test/recording.mp4" "test-room"
```

#### Meeting Creation Failures

**Symptoms**: HTTP 500 errors when creating meetings

**Solutions**:
1. Check Reflector logs for JWT generation errors
2. Verify all required environment variables are set
3. Ensure Jitsi domain is accessible from Reflector
4. Test JWT secret configuration

### Debug Commands

```bash
# Verify Prosody configuration
sudo prosodyctl check config

# Check Jitsi services status
sudo systemctl status prosody jicofo jitsi-videobridge2

# Test JWT generation
curl -X POST "https://your-reflector-domain.com/v1/rooms/test/meeting" \
  -H "Authorization: Bearer $TOKEN" -v

# Monitor webhook events
sudo tail -f /var/log/reflector/app.log | grep jitsi

# Check SSL certificates
sudo certbot certificates
```

### Performance Optimization

#### Scaling Considerations

**Single Server Limits:**
- ~50 concurrent participants per JVB instance
- ~10 concurrent Jibri recordings
- CPU and bandwidth become bottlenecks

**Multi-Server Setup:**
- Multiple JVB instances for scaling
- Dedicated Jibri recording servers
- Load balancing for high availability

#### Resource Monitoring

```bash
# Monitor JVB performance
sudo systemctl status jitsi-videobridge2
sudo journalctl -u jitsi-videobridge2 -f

# Check Prosody connections
sudo prosodyctl mod_admin_telnet
> c2s:show()
> muc:rooms()
```

## Security Best Practices

### JWT Security
- Use strong, unique secrets (32+ characters)
- Rotate JWT secrets regularly
- Implement proper token expiration
- Never log or expose JWT tokens

### Network Security
- Use HTTPS/WSS for all communications
- Implement proper firewall rules
- Consider VPN for server-to-server communication
- Monitor for unauthorized access attempts

### Recording Security
- Encrypt recordings at rest
- Implement access controls for recording files
- Regular security audits of file permissions
- Comply with data protection regulations

## Migration from Whereby

If migrating from Whereby to Jitsi:

1. **Parallel Setup** - Configure Jitsi alongside existing Whereby
2. **Room Migration** - Update room platform field to "jitsi"
3. **Test Integration** - Verify meeting creation and webhooks
4. **User Training** - Different UI and feature set
5. **Monitor Performance** - Watch for issues during transition
6. **Cleanup** - Remove Whereby configuration when stable

## Support and Resources

### Jitsi Community Resources
- **Documentation**: [jitsi.github.io/handbook](https://jitsi.github.io/handbook/)
- **Community Forum**: [community.jitsi.org](https://community.jitsi.org/)
- **GitHub Issues**: [github.com/jitsi/jitsi-meet](https://github.com/jitsi/jitsi-meet)

### Professional Support
- **8x8 Commercial Support** - Professional Jitsi hosting and support
- **Community Consulting** - Third-party Jitsi implementation services

### Monitoring and Maintenance
- Monitor system resources (CPU, memory, bandwidth)
- Regular security updates for all components
- Backup configuration files and certificates
- Test disaster recovery procedures