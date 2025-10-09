# Daily.co Integration Test Plan

## Prerequisites

**1. Environment Variables** (check in `.env.development.local`):
```bash
DAILY_API_KEY=<key>
DAILY_SUBDOMAIN=monadical
DAILY_WEBHOOK_SECRET=<base64-encoded-secret>
AWS_DAILY_S3_BUCKET=reflector-dailyco-local
AWS_DAILY_S3_REGION=us-east-1
AWS_DAILY_ROLE_ARN=arn:aws:iam::950402358378:role/DailyCo
DAILY_MIGRATION_ENABLED=true
DAILY_MIGRATION_ROOM_IDS=["552640fd-16f2-4162-9526-8cf40cd2357e"]
```

**2. Services Running:**
```bash
docker-compose ps  # server, postgres, redis should be UP
```

**3. ngrok Tunnel for Webhooks:**
```bash
ngrok http 1250  # Note the URL (e.g., https://abc123.ngrok-free.app)
```

**4. Webhook Created:**
```bash
cd server
uv run python scripts/recreate_daily_webhook.py https://abc123.ngrok-free.app/v1/daily/webhook
# Verify: "Created webhook <uuid> (state: ACTIVE)"
```

---

## Test 1: Database Configuration

**Check room platform:**
```bash
docker-compose exec -T postgres psql -U reflector -d reflector -c \
  "SELECT id, name, platform, recording_type FROM room WHERE name = 'test2';"
```

**Expected:**
```
id: 552640fd-16f2-4162-9526-8cf40cd2357e
name: test2
platform: whereby  # DB value (overridden by env var DAILY_MIGRATION_ROOM_IDS)
recording_type: cloud
```

**Clear old meetings:**
```bash
docker-compose exec -T postgres psql -U reflector -d reflector -c \
  "UPDATE meeting SET is_active = false WHERE room_id = '552640fd-16f2-4162-9526-8cf40cd2357e';"
```

---

## Test 2: Meeting Creation with Auto-Recording

**Create meeting:**
```bash
curl -s -X POST http://localhost:1250/v1/rooms/test2/meeting \
  -H "Content-Type: application/json" \
  -d '{"allow_duplicated":false}' | python3 -m json.tool
```

**Expected Response:**
```json
{
  "room_name": "test2-YYYYMMDDHHMMSS",  // Includes "test2" prefix!
  "room_url": "https://monadical.daily.co/test2-...?t=<JWT_TOKEN>",  // Has token!
  "platform": "daily",
  "recording_type": "cloud"  // DB value (Whereby-specific)
}
```

**Decode token to verify auto-recording:**
```bash
# Extract token from room_url, decode JWT payload
echo "<token>" | python3 -c "
import sys, json, base64
token = sys.stdin.read().strip()
payload = token.split('.')[1] + '=' * (4 - len(token.split('.')[1]) % 4)
print(json.dumps(json.loads(base64.b64decode(payload)), indent=2))
"
```

**Expected token payload:**
```json
{
  "r": "test2-YYYYMMDDHHMMSS",  // Room name
  "sr": true,  // start_recording: true ✅
  "d": "...",  // Domain ID
  "iat": 1234567890
}
```

---

## Test 3: Daily.co API Verification

**Check room configuration:**
```bash
ROOM_NAME="<from previous step>"
curl -s -X GET "https://api.daily.co/v1/rooms/$ROOM_NAME" \
  -H "Authorization: Bearer $DAILY_API_KEY" | python3 -m json.tool
```

**Expected config:**
```json
{
  "config": {
    "enable_recording": "raw-tracks",  // ✅
    "recordings_bucket": {
      "bucket_name": "reflector-dailyco-local",
      "bucket_region": "us-east-1",
      "assume_role_arn": "arn:aws:iam::950402358378:role/DailyCo"
    }
  }
}
```

---

## Test 4: Browser UI Test (Playwright MCP)

**Load room:**
```javascript
await page.goto('http://localhost:3000/test2');
await new Promise(f => setTimeout(f, 12000));  // Wait for load
```

**Verify Daily.co iframe loaded:**
```javascript
const iframes = document.querySelectorAll('iframe');
// Expected: 1 iframe with src containing "monadical.daily.co"
```

**Take screenshot:**
```javascript
await page.screenshot({ path: 'test2-before-join.png' });
// Expected: Daily.co pre-call UI visible
```

**Join meeting:**
```javascript
await page.locator('iframe').contentFrame().getByRole('button', { name: 'Join' }).click();
await new Promise(f => setTimeout(f, 5000));
```

**Verify in-call:**
```javascript
await page.screenshot({ path: 'test2-in-call.png' });
// Expected: "Waiting for others to join" or participant video visible
```

**Leave meeting:**
```javascript
await page.locator('iframe').contentFrame().getByRole('button', { name: 'Leave' }).click();
```

---

## Test 5: Webhook Verification

**Check server logs for webhooks:**
```bash
docker-compose logs --since 15m server 2>&1 | grep -i "participant joined\|recording started"
```

**Expected logs:**
```
[info] Participant joined | meeting_id=... | num_clients=1 | recording_type=cloud | recording_trigger=automatic-2nd-participant
[info] Recording started | meeting_id=... | recording_id=... | platform=daily
```

**Check Daily.co webhook delivery logs:**
```bash
curl -s -X GET "https://api.daily.co/v1/logs/webhooks?limit=20" \
  -H "Authorization: Bearer $DAILY_API_KEY" | python3 -c "
import sys, json
logs = json.load(sys.stdin)
for log in logs[:10]:
    req = json.loads(log['request'])
    room = req.get('payload', {}).get('room') or req.get('payload', {}).get('room_name', 'N/A')
    print(f\"{req['type']:30s} | room: {room:30s} | status: {log['status']}\")
"
```

**Expected output:**
```
participant.joined             | room: test2-YYYYMMDDHHMMSS       | status: 200
recording.started              | room: test2-YYYYMMDDHHMMSS       | status: 200
participant.left               | room: test2-YYYYMMDDHHMMSS       | status: 200
recording.ready-to-download    | room: test2-YYYYMMDDHHMMSS       | status: 200
```

**Check database updated:**
```bash
docker-compose exec -T postgres psql -U reflector -d reflector -c \
  "SELECT room_name, num_clients FROM meeting WHERE room_name LIKE 'test2-%' ORDER BY end_date DESC LIMIT 1;"
```

**Expected:**
```
room_name: test2-YYYYMMDDHHMMSS
num_clients: 0  // After participant left
```

---

## Test 6: Recording in S3

**List recent recordings:**
```bash
curl -s -X GET "https://api.daily.co/v1/recordings" \
  -H "Authorization: Bearer $DAILY_API_KEY" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for rec in data.get('data', [])[:5]:
    if 'test2-' in rec.get('room_name', ''):
        print(f\"Room: {rec['room_name']}\")
        print(f\"Status: {rec['status']}\")
        print(f\"Duration: {rec.get('duration', 0)}s\")
        print(f\"S3 key: {rec.get('s3key', 'N/A')}\")
        print(f\"Tracks: {len(rec.get('tracks', []))} files\")
        for track in rec.get('tracks', []):
            print(f\"  - {track['type']}: {track['s3Key'].split('/')[-1]} ({track['size']} bytes)\")
        print()
"
```

**Expected output:**
```
Room: test2-20251009192341
Status: finished
Duration: ~30-120s
S3 key: monadical/test2-20251009192341/1760037914930
Tracks: 2 files
  - audio: 1760037914930-<uuid>-cam-audio-1760037915265 (~400 KB)
  - video: 1760037914930-<uuid>-cam-video-1760037915269 (~10-30 MB)
```

**Verify S3 path structure:**
- `monadical/` - Daily.co subdomain
- `test2-20251009192341/` - Reflector room name + timestamp
- `<timestamp>-<participant-uuid>-<media-type>-<track-start>.webm` - Individual track files

---

## Test 7: Recording Type Verification

**Check what Daily.co received:**
```bash
curl -s -X GET "https://api.daily.co/v1/rooms/test2-<timestamp>" \
  -H "Authorization: Bearer $DAILY_API_KEY" | python3 -m json.tool | grep "enable_recording"
```

**Expected:**
```json
"enable_recording": "raw-tracks"
```

**NOT:** `"enable_recording": "cloud"` (that would be wrong - we want raw tracks)

---

## Troubleshooting

### Issue: No webhooks received

**Check webhook state:**
```bash
curl -s -X GET "https://api.daily.co/v1/webhooks" \
  -H "Authorization: Bearer $DAILY_API_KEY" | python3 -m json.tool
```

**If state is FAILED:**
```bash
cd server
uv run python scripts/recreate_daily_webhook.py https://<ngrok-url>/v1/daily/webhook
```

### Issue: Webhooks return 422

**Check server logs:**
```bash
docker-compose logs --tail=50 server | grep "Failed to parse webhook event"
```

**Common cause:** Event structure mismatch. Daily.co events use:
```json
{
  "version": "1.0.0",
  "type": "participant.joined",
  "payload": {...},  // NOT "data"
  "event_ts": 123.456  // NOT "ts"
}
```

### Issue: Recording not starting

1. **Check token has `sr: true`:**
   - Decode JWT token from room_url query param
   - Should contain `"sr": true`

2. **Check Daily.co room config:**
   - `enable_recording` must be set (not false)
   - For raw-tracks: must be exactly `"raw-tracks"`

3. **Check participant actually joined:**
   - Logs should show "Participant joined"
   - Must click "Join" button, not just pre-call screen

### Issue: Recording in S3 but wrong format

**Daily.co recording types:**
- `"cloud"` → Single MP4 file (`download_link` in webhook)
- `"raw-tracks"` → Multiple WebM files (`tracks` array in webhook)
- `"raw-tracks-audio-only"` → Only audio WebM files

**Current implementation:** Always uses `"raw-tracks"` (better for transcription)

---

## Quick Validation Commands

**One-liner to verify everything:**
```bash
# 1. Check room exists
docker-compose exec -T postgres psql -U reflector -d reflector -c \
  "SELECT name, platform FROM room WHERE name = 'test2';" && \

# 2. Create meeting
MEETING=$(curl -s -X POST http://localhost:1250/v1/rooms/test2/meeting \
  -H "Content-Type: application/json" -d '{"allow_duplicated":false}') && \
echo "$MEETING" | python3 -c "import sys,json; m=json.load(sys.stdin); print(f'Room: {m[\"room_name\"]}\nURL: {m[\"room_url\"][:80]}...')" && \

# 3. Check Daily.co config
ROOM_NAME=$(echo "$MEETING" | python3 -c "import sys,json; print(json.load(sys.stdin)['room_name'])") && \
curl -s -X GET "https://api.daily.co/v1/rooms/$ROOM_NAME" \
  -H "Authorization: Bearer $DAILY_API_KEY" | python3 -c "import sys,json; print(f'Recording: {json.load(sys.stdin)[\"config\"][\"enable_recording\"]}')"
```

**Expected output:**
```
name: test2, platform: whereby
Room: test2-20251009192341
URL: https://monadical.daily.co/test2-20251009192341?t=eyJhbGc...
Recording: raw-tracks
```

---

## Success Criteria Checklist

- [x] Room name includes Reflector room prefix (`test2-...`)
- [x] Meeting URL contains JWT token (`?t=...`)
- [x] Token has `sr: true` (auto-recording enabled)
- [x] Daily.co room config: `enable_recording: "raw-tracks"`
- [x] Browser loads Daily.co interface (not Whereby)
- [x] Recording auto-starts when participant joins
- [x] Webhooks received: participant.joined, recording.started, participant.left, recording.ready-to-download
- [x] Recording status: `finished`
- [x] S3 contains 2 files: audio (.webm) and video (.webm)
- [x] S3 path: `monadical/test2-{timestamp}/{recording-start-ts}-{participant-uuid}-cam-{audio|video}-{track-start-ts}`
- [x] Database `num_clients` increments/decrements correctly
