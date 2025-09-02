# Jitsi Integration Configuration Guide

This guide provides step-by-step instructions for configuring Reflector to work with a self-hosted Jitsi Meet installation for video meetings and recording.

## Prerequisites

Before configuring Jitsi integration, ensure you have:

- **Self-hosted Jitsi Meet installation** (version 2.0.8922 or later recommended)
- **Jibri recording service** configured and running
- **Prosody XMPP server** with mod_event_sync module installed
- **Docker or system deployment** of Reflector with access to environment variables
- **SSL certificates** for secure communication between services

## Environment Configuration

Add the following environment variables to your Reflector deployment:

### Required Settings

```bash
# Jitsi Meet domain (without https://)
JITSI_DOMAIN=meet.example.com

# JWT secret for room authentication (generate with: openssl rand -hex 32)
JITSI_JWT_SECRET=your-64-character-hex-secret-here

# Webhook secret for secure event handling (generate with: openssl rand -hex 16)
JITSI_WEBHOOK_SECRET=your-32-character-hex-secret-here

# Application identifier (should match Jitsi configuration)
JITSI_APP_ID=reflector

# JWT issuer and audience (should match Jitsi configuration)
JITSI_JWT_ISSUER=reflector
JITSI_JWT_AUDIENCE=jitsi
```

### Example .env Configuration

```bash
# Add to your server/.env file
JITSI_DOMAIN=meet.mycompany.com
JITSI_JWT_SECRET=$(openssl rand -hex 32)
JITSI_WEBHOOK_SECRET=$(openssl rand -hex 16)
JITSI_APP_ID=reflector
JITSI_JWT_ISSUER=reflector
JITSI_JWT_AUDIENCE=jitsi
```

## Jitsi Meet Server Configuration

### 1. JWT Authentication Setup

Edit `/etc/prosody/conf.d/[YOUR_DOMAIN].cfg.lua`:

```lua
VirtualHost "meet.example.com"
    authentication = "token"
    app_id = "reflector"
    app_secret = "your-jwt-secret-here"

    -- Allow anonymous access for non-authenticated users
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
        "event_sync";  -- Required for webhook events
    }
```

### 2. Room Access Control

Edit `/etc/jitsi/meet/meet.example.com-config.js`:

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

    // Reflector-specific settings
    prejoinPageEnabled: true,
    requireDisplayName: true,
};
```

### 3. Interface Configuration

Edit `/usr/share/jitsi-meet/interface_config.js`:

```javascript
var interfaceConfig = {
    // Customize for Reflector branding
    APP_NAME: 'Reflector Meeting',
    DEFAULT_WELCOME_PAGE_LOGO_URL: 'https://your-domain.com/logo.png',

    // Hide unnecessary buttons
    TOOLBAR_BUTTONS: [
        'microphone', 'camera', 'closedcaptions', 'desktop',
        'fullscreen', 'fodeviceselection', 'hangup',
        'chat', 'recording', 'livestreaming', 'etherpad',
        'sharedvideo', 'settings', 'raisehand', 'videoquality',
        'filmstrip', 'invite', 'feedback', 'stats', 'shortcuts',
        'tileview', 'videobackgroundblur', 'download', 'help',
        'mute-everyone'
    ]
};
```

## Jibri Configuration

### 1. Recording Service Setup

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

### 2. Finalize Script Setup

Create `/opt/jitsi/jibri/finalize.sh`:

```bash
#!/bin/bash
# Jibri finalize script for Reflector integration

RECORDING_FILE="$1"
ROOM_NAME="$2"
REFLECTOR_API_URL="${REFLECTOR_API_URL:-http://localhost:1250}"
WEBHOOK_SECRET="${JITSI_WEBHOOK_SECRET}"

# Generate webhook signature
generate_signature() {
    local payload="$1"
    echo -n "$payload" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | cut -d' ' -f2
}

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
SIGNATURE=$(generate_signature "$PAYLOAD")

# Send webhook to Reflector
curl -X POST "$REFLECTOR_API_URL/v1/jibri/recording-complete" \
    -H "Content-Type: application/json" \
    -H "X-Jitsi-Signature: $SIGNATURE" \
    -d "$PAYLOAD" \
    --max-time 30

echo "Recording finalization webhook sent for room: $ROOM_NAME"
```

Make the script executable:

```bash
chmod +x /opt/jitsi/jibri/finalize.sh
```

## Prosody Event Configuration

### 1. Event-Sync Module Installation

Install the mod_event_sync module:

```bash
# Download the module
cd /usr/share/jitsi-meet/prosody-plugins/
wget https://raw.githubusercontent.com/jitsi-contrib/prosody-plugins/main/mod_event_sync.lua

# Or if using git
git clone https://github.com/jitsi-contrib/prosody-plugins.git
cp prosody-plugins/mod_event_sync.lua /usr/share/jitsi-meet/prosody-plugins/
```

### 2. Webhook Configuration

Add to `/etc/prosody/conf.d/[YOUR_DOMAIN].cfg.lua`:

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
```

### 3. Restart Services

After configuration changes, restart all services:

```bash
systemctl restart prosody
systemctl restart jicofo
systemctl restart jitsi-videobridge2
systemctl restart jibri
systemctl restart nginx
```

## Reflector Room Configuration

### 1. Create Jitsi Room

When creating rooms in Reflector, set the platform field:

```bash
curl -X POST "https://your-reflector-domain.com/v1/rooms" \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "my-jitsi-room",
        "platform": "jitsi",
        "recording_type": "cloud",
        "recording_trigger": "automatic-2nd-participant",
        "is_locked": false,
        "room_mode": "normal"
    }'
```

### 2. Meeting Creation

Meetings will automatically use Jitsi when the room platform is set to "jitsi":

```bash
curl -X POST "https://your-reflector-domain.com/v1/rooms/my-jitsi-room/meeting" \
    -H "Authorization: Bearer $AUTH_TOKEN"
```

## Testing the Integration

### 1. Health Check

Verify Jitsi webhook configuration:

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

### 2. Room Creation Test

1. Create a Jitsi room via Reflector API
2. Start a meeting - should generate Jitsi Meet URL with JWT token
3. Join with multiple participants - should trigger participant events
4. Start recording - should trigger Jibri recording workflow

### 3. Webhook Event Test

Monitor Reflector logs for incoming webhook events:

```bash
# Check for participant events
curl -X POST "https://your-reflector-domain.com/v1/jitsi/events" \
    -H "Content-Type: application/json" \
    -H "X-Jitsi-Signature: test-signature" \
    -d '{
        "event": "muc-occupant-joined",
        "room": "test-room-name",
        "timestamp": "2025-01-15T10:30:00.000Z",
        "data": {}
    }'
```

## Troubleshooting

### Common Issues

#### JWT Authentication Failures

**Symptoms:** Users can't join rooms, "Authentication failed" errors

**Solutions:**
1. Verify JWT secret matches between Jitsi and Reflector
2. Check JWT token expiration (default 8 hours)
3. Ensure system clocks are synchronized
4. Validate JWT issuer/audience configuration

```bash
# Debug JWT tokens
echo "JWT_TOKEN_HERE" | cut -d'.' -f2 | base64 -d | jq
```

#### Webhook Events Not Received

**Symptoms:** Participant counts not updating, recording events missing

**Solutions:**
1. Verify event_sync module is loaded in Prosody
2. Check webhook URL accessibility from Jitsi server
3. Validate webhook signature generation
4. Review Prosody and Reflector logs

```bash
# Test webhook connectivity
curl -v "https://your-reflector-domain.com/v1/jitsi/health"

# Check Prosody logs
tail -f /var/log/prosody/prosody.log

# Check Reflector logs
docker logs your-reflector-container
```

#### Recording Issues

**Symptoms:** Recordings not starting, finalize script errors

**Solutions:**
1. Verify Jibri service status and configuration
2. Check recording directory permissions
3. Validate finalize script execution permissions
4. Monitor Jibri logs for errors

```bash
# Check Jibri status
systemctl status jibri

# Test finalize script
sudo -u jibri /opt/jitsi/jibri/finalize.sh "/test/recording.mp4" "test-room"

# Check Jibri logs
journalctl -u jibri -f
```

### Debug Commands

```bash
# Verify Jitsi configuration
prosodyctl check config

# Test JWT generation
curl -X POST "https://your-reflector-domain.com/v1/rooms/test/meeting" \
    -H "Authorization: Bearer $TOKEN" -v

# Monitor webhook events
tail -f /var/log/reflector/app.log | grep jitsi

# Check room participant counts
curl "https://your-reflector-domain.com/v1/rooms" \
    -H "Authorization: Bearer $TOKEN" | jq '.data[].num_clients'
```

### Performance Optimization

#### For High-Concurrent Usage

1. **Jitsi Videobridge Tuning:**
```bash
# /etc/jitsi/videobridge/sip-communicator.properties
org.jitsi.videobridge.STATISTICS_INTERVAL=5000
org.jitsi.videobridge.load.INITIAL_STREAM_LIMIT=50
```

2. **Database Connection Pooling:**
```python
# In your Reflector settings
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30
```

3. **Redis Configuration:**
```bash
# For webhook event caching
REDIS_URL=redis://localhost:6379/1
WEBHOOK_EVENT_TTL=3600
```

## Security Considerations

### Network Security
- Use HTTPS/WSS for all communications
- Implement proper firewall rules
- Consider VPN for server-to-server communication

### Authentication Security
- Rotate JWT secrets regularly
- Use strong webhook secrets (32+ characters)
- Implement rate limiting on webhook endpoints

### Recording Security
- Encrypt recordings at rest
- Implement access controls for recording files
- Regular security audits of file permissions

## Support

For additional support:

1. **Reflector Issues:** Check GitHub issues or create new ones
2. **Jitsi Community:** [Community Forum](https://community.jitsi.org/)
3. **Documentation:** [Jitsi Developer Guide](https://jitsi.github.io/handbook/)

## Migration from Whereby

If migrating from Whereby integration:

1. Update existing rooms to use "jitsi" platform
2. Verify webhook configurations are updated
3. Test recording workflows thoroughly
4. Monitor participant event accuracy
5. Update any custom integrations using meeting APIs

The platform abstraction layer ensures smooth migration with minimal API changes.