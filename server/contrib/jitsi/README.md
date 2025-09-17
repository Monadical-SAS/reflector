# Event Logger for Docker-Jitsi-Meet

A Prosody module that logs Jitsi meeting events to JSONL files alongside recordings, enabling complete participant tracking and speaker statistics.

## Prerequisites

- Running docker-jitsi-meet installation
- Jibri configured for recording

## Installation

### Step 1: Copy the Module

Copy the Prosody module to your custom plugins directory:

```bash
# Create the directory if it doesn't exist
mkdir -p ~/.jitsi-meet-cfg/prosody/prosody-plugins-custom

# Copy the module
cp mod_event_logger.lua ~/.jitsi-meet-cfg/prosody/prosody-plugins-custom/
```

### Step 2: Update Your .env File

Add or modify these variables in your `.env` file:

```bash
# If XMPP_MUC_MODULES already exists, append event_logger
# Example: XMPP_MUC_MODULES=existing_module,event_logger
XMPP_MUC_MODULES=event_logger

# Optional: Configure the module (these are defaults)
JIBRI_RECORDINGS_PATH=/config/recordings
JIBRI_LOG_SPEAKER_STATS=true
JIBRI_SPEAKER_STATS_INTERVAL=10
```

**Important**: If you already have `XMPP_MUC_MODULES` defined, add `event_logger` to the comma-separated list:
```bash
# Existing modules + our module
XMPP_MUC_MODULES=mod_info,mod_alert,event_logger
```

### Step 3: Modify docker-compose.yml

Add a shared recordings volume so Prosody can write events alongside Jibri recordings:

```yaml
services:
  prosody:
    # ... existing configuration ...
    volumes:
      - ${CONFIG}/prosody/config:/config:Z
      - ${CONFIG}/prosody/prosody-plugins-custom:/prosody-plugins-custom:Z
      - ${CONFIG}/recordings:/config/recordings:Z  # Add this line
    environment:
      # Add if not using .env file
      - XMPP_MUC_MODULES=${XMPP_MUC_MODULES:-event_logger}
      - JIBRI_RECORDINGS_PATH=/config/recordings

  jibri:
    # ... existing configuration ...
    volumes:
      - ${CONFIG}/jibri:/config:Z
      - ${CONFIG}/recordings:/config/recordings:Z  # Add this line
    environment:
      # For Reflector webhook integration (optional)
      - REFLECTOR_WEBHOOK_URL=${REFLECTOR_WEBHOOK_URL:-}
      - JIBRI_FINALIZE_RECORDING_SCRIPT_PATH=/config/finalize.sh
```

### Step 4: Add Finalize Script (Optional - For Reflector Integration)

If you want to notify Reflector when recordings complete:

```bash
# Copy the finalize script
cp finalize.sh ~/.jitsi-meet-cfg/jibri/finalize.sh
chmod +x ~/.jitsi-meet-cfg/jibri/finalize.sh

# Add to .env
REFLECTOR_WEBHOOK_URL=http://your-reflector-api:8000
```

### Step 5: Restart Services

```bash
docker-compose down
docker-compose up -d
```

## What Gets Created

After a recording, you'll find in `~/.jitsi-meet-cfg/recordings/{session-id}/`:
- `recording.mp4` - The video recording (created by Jibri)
- `metadata.json` - Basic metadata (created by Jibri)
- `events.jsonl` - Complete participant timeline (created by this module)

## Event Format

Each line in `events.jsonl` is a JSON object:

```json
{"type":"room_created","timestamp":1234567890,"room_name":"TestRoom","room_jid":"testroom@conference.meet.jitsi","meeting_url":"https://meet.jitsi/TestRoom"}
{"type":"recording_started","timestamp":1234567891,"room_name":"TestRoom","session_id":"20240115120000_TestRoom","jibri_jid":"jibri@recorder.meet.jitsi"}
{"type":"participant_joined","timestamp":1234567892,"room_name":"TestRoom","participant":{"jid":"user1@meet.jitsi/web","nick":"John Doe","id":"user1@meet.jitsi","is_moderator":false}}
{"type":"speaker_active","timestamp":1234567895,"room_name":"TestRoom","speaker_jid":"user1@meet.jitsi","speaker_nick":"John Doe","duration":10}
{"type":"participant_left","timestamp":1234567920,"room_name":"TestRoom","participant":{"jid":"user1@meet.jitsi/web","nick":"John Doe","duration_seconds":28}}
{"type":"recording_stopped","timestamp":1234567950,"room_name":"TestRoom","session_id":"20240115120000_TestRoom","meeting_url":"https://meet.jitsi/TestRoom"}
```

## Configuration Options

All configuration can be done via environment variables:

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `JIBRI_RECORDINGS_PATH` | `/config/recordings` | Path where recordings are stored |
| `JIBRI_LOG_SPEAKER_STATS` | `true` | Enable speaker statistics logging |
| `JIBRI_SPEAKER_STATS_INTERVAL` | `10` | Seconds between speaker stats updates |

## Verifying Installation

Check that the module is loaded:
```bash
docker-compose logs prosody | grep "Event Logger"
# Should see: "Event Logger loaded - writing to /config/recordings"
```

Check for events after a recording:
```bash
ls -la ~/.jitsi-meet-cfg/recordings/*/events.jsonl
cat ~/.jitsi-meet-cfg/recordings/*/events.jsonl | jq .
```

## Troubleshooting

### No events.jsonl file created

1. **Check module is enabled**:
   ```bash
   docker-compose exec prosody grep -r "event_logger" /config
   ```

2. **Verify volume permissions**:
   ```bash
   docker-compose exec prosody ls -la /config/recordings
   ```

3. **Check Prosody logs for errors**:
   ```bash
   docker-compose logs prosody | grep -i error
   ```

### Module not loading

1. **Verify file exists in container**:
   ```bash
   docker-compose exec prosody ls -la /prosody-plugins-custom/
   ```

2. **Check XMPP_MUC_MODULES format** (must be comma-separated, no spaces):
   - ✅ Correct: `XMPP_MUC_MODULES=mod1,mod2,event_logger`
   - ❌ Wrong: `XMPP_MUC_MODULES=mod1, mod2, event_logger`

## Common docker-compose.yml Patterns

### Minimal Addition (if you trust defaults)
```yaml
services:
  prosody:
    volumes:
      - ${CONFIG}/recordings:/config/recordings:Z  # Just add this
```

### Full Configuration
```yaml
services:
  prosody:
    volumes:
      - ${CONFIG}/prosody/config:/config:Z
      - ${CONFIG}/prosody/prosody-plugins-custom:/prosody-plugins-custom:Z
      - ${CONFIG}/recordings:/config/recordings:Z
    environment:
      - XMPP_MUC_MODULES=event_logger
      - JIBRI_RECORDINGS_PATH=/config/recordings
      - JIBRI_LOG_SPEAKER_STATS=true
      - JIBRI_SPEAKER_STATS_INTERVAL=10

  jibri:
    volumes:
      - ${CONFIG}/jibri:/config:Z
      - ${CONFIG}/recordings:/config/recordings:Z
    environment:
      - JIBRI_RECORDING_DIR=/config/recordings
      - JIBRI_FINALIZE_RECORDING_SCRIPT_PATH=/config/finalize.sh
```

## Integration with Reflector

The finalize.sh script will automatically notify Reflector when a recording completes if `REFLECTOR_WEBHOOK_URL` is set. Reflector will receive:

```json
{
  "session_id": "20240115120000_TestRoom",
  "path": "20240115120000_TestRoom",
  "meeting_url": "https://meet.jitsi/TestRoom"
}
```

Reflector then processes the recording along with the complete participant timeline from `events.jsonl`.