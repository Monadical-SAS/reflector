# Daily.co Integration Test Plan

## ✅ IMPLEMENTATION STATUS: Real Transcription Active

**This test validates Daily.co multitrack recording integration with REAL transcription/diarization.**

The implementation includes complete audio processing pipeline:
- **Multitrack recordings** from Daily.co S3 (separate audio stream per participant)
- **PyAV-based audio mixdown** with PTS-based track alignment
- **Real transcription** via Modal GPU backend (Whisper)
- **Real diarization** via Modal GPU backend (speaker identification)
- **Per-track transcription** with timestamp synchronization
- **Complete database entities** (recording, transcript, topics, participants, words)

**Processing pipeline** (`PipelineMainMultitrack`):
1. Download all audio tracks from Daily.co S3
2. Align tracks by PTS (presentation timestamp) to handle late joiners
3. Mix tracks into single audio file for unified playback
4. Transcribe each track individually with proper offset handling
5. Perform diarization on mixed audio
6. Generate topics, summaries, and word-level timestamps
7. Convert audio to MP3 and generate waveform visualization

**Note:** A stub processor (`process_daily_recording`) exists for testing webhook flow without GPU costs, but the production code path uses `process_multitrack_recording` with full ML pipeline.

---

## Prerequisites

**1. Environment Variables** (check in `.env.development.local`):
```bash
# Daily.co API Configuration
DAILY_API_KEY=<key>
DAILY_SUBDOMAIN=monadical
DAILY_WEBHOOK_SECRET=<base64-encoded-secret>
AWS_DAILY_S3_BUCKET=reflector-dailyco-local
AWS_DAILY_S3_REGION=us-east-1
AWS_DAILY_ROLE_ARN=arn:aws:iam::950402358378:role/DailyCo
DAILY_MIGRATION_ENABLED=true
DAILY_MIGRATION_ROOM_IDS=["552640fd-16f2-4162-9526-8cf40cd2357e"]

# Transcription/Diarization Backend (Required for real processing)
DIARIZATION_BACKEND=modal
DIARIZATION_MODAL_API_KEY=<modal-api-key>
# TRANSCRIPTION_BACKEND is not explicitly set (uses default/modal)
```

**2. Services Running:**
```bash
docker compose ps  # server, postgres, redis, worker, beat should be UP
```

**IMPORTANT:** Worker and beat services MUST be running for transcription processing:
```bash
docker compose up -d worker beat
```

**3. ngrok Tunnel for Webhooks:**
```bash
# Start ngrok (if not already running)
ngrok http 1250 --log=stdout > /tmp/ngrok.log 2>&1 &

# Get public URL
curl -s http://localhost:4040/api/tunnels | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['tunnels'][0]['public_url'])"
```

**Current ngrok URL:** `https://0503947384a3.ngrok-free.app` (as of last registration)

**4. Webhook Created:**
```bash
cd server
uv run python scripts/recreate_daily_webhook.py https://0503947384a3.ngrok-free.app/v1/daily/webhook
# Verify: "Created webhook <uuid> (state: ACTIVE)"
```

**Current webhook status:** ✅ ACTIVE (webhook ID: dad5ad16-ceca-488e-8fc5-dae8650b51d0)

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

**Using Claude Code MCP tools:**

**Load room:**
```
Use: mcp__playwright__browser_navigate
Input: {"url": "http://localhost:3000/test2"}

Then wait 12 seconds for iframe to load
```

**Verify Daily.co iframe loaded:**
```
Use: mcp__playwright__browser_snapshot

Expected in snapshot:
- iframe element with src containing "monadical.daily.co"
- Daily.co pre-call UI visible
```

**Take screenshot:**
```
Use: mcp__playwright__browser_take_screenshot
Input: {"filename": "test2-before-join.png"}

Expected: Daily.co pre-call UI with "Join" button visible
```

**Join meeting:**
```
Note: Daily.co iframe interaction requires clicking inside iframe.
Use: mcp__playwright__browser_click
Input: {"element": "Join button in Daily.co iframe", "ref": "<ref-from-snapshot>"}

Then wait 5 seconds for call to connect
```

**Verify in-call:**
```
Use: mcp__playwright__browser_take_screenshot
Input: {"filename": "test2-in-call.png"}

Expected: "Waiting for others to join" or participant video visible
```

**Leave meeting:**
```
Use: mcp__playwright__browser_click
Input: {"element": "Leave button in Daily.co iframe", "ref": "<ref-from-snapshot>"}
```

---

**Alternative: JavaScript snippets (for manual testing):**

```javascript
await page.goto('http://localhost:3000/test2');
await new Promise(f => setTimeout(f, 12000));  // Wait for load

// Verify iframe
const iframes = document.querySelectorAll('iframe');
// Expected: 1 iframe with src containing "monadical.daily.co"

// Screenshot
await page.screenshot({ path: 'test2-before-join.png' });

// Join
await page.locator('iframe').contentFrame().getByRole('button', { name: 'Join' }).click();
await new Promise(f => setTimeout(f, 5000));

// In-call screenshot
await page.screenshot({ path: 'test2-in-call.png' });

// Leave
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

## Test 7: Database Check - Recording and Transcript

**Check recording created:**
```bash
docker-compose exec -T postgres psql -U reflector -d reflector -c \
  "SELECT id, bucket_name, object_key, status, meeting_id, recorded_at
   FROM recording
   ORDER BY recorded_at DESC LIMIT 1;"
```

**Expected:**
```
id: <recording-id-from-webhook>
bucket_name: reflector-dailyco-local
object_key: monadical/test2-<timestamp>/<recording-timestamp>-<uuid>-cam-audio-<track-start>.webm
status: completed
meeting_id: <meeting-id>
recorded_at: <recent-timestamp>
```

**Check transcript created:**
```bash
docker compose exec -T postgres psql -U reflector -d reflector -c \
  "SELECT id, title, status, duration, recording_id, meeting_id, room_id
   FROM transcript
   ORDER BY created_at DESC LIMIT 1;"
```

**Expected (REAL transcription):**
```
id: <transcript-id>
title: <AI-generated title based on actual conversation content>
status: uploaded  (audio file processed and available)
duration: <actual meeting duration in seconds>
recording_id: <same-as-recording-id-above>
meeting_id: <meeting-id>
room_id: 552640fd-16f2-4162-9526-8cf40cd2357e
```

**Note:** Title and content will reflect the ACTUAL conversation, not mock data. Processing time depends on recording length and GPU backend availability (Modal).

**Verify audio file exists:**
```bash
ls -lh data/<transcript-id>/upload.webm
```

**Expected:**
```
-rw-r--r-- 1 user staff ~100-200K Oct 10 18:48 upload.webm
```

**Check transcript topics (REAL transcription):**
```bash
TRANSCRIPT_ID=$(docker compose exec -T postgres psql -U reflector -d reflector -t -c \
  "SELECT id FROM transcript ORDER BY created_at DESC LIMIT 1;")

docker compose exec -T postgres psql -U reflector -d reflector -c \
  "SELECT
     jsonb_array_length(topics) as num_topics,
     jsonb_array_length(participants) as num_participants,
     short_summary,
     title
   FROM transcript
   WHERE id = '$TRANSCRIPT_ID';"
```

**Expected (REAL data):**
```
num_topics: <varies based on conversation>
num_participants: <actual number of participants who spoke>
short_summary: <AI-generated summary of actual conversation>
title: <AI-generated title based on content>
```

**Check topics contain actual transcription:**
```bash
docker compose exec -T postgres psql -U reflector -d reflector -c \
  "SELECT topics->0->'title', topics->0->'summary', topics->0->'transcript'
   FROM transcript
   ORDER BY created_at DESC LIMIT 1;" | head -20
```

**Expected output:** Will contain the ACTUAL transcribed conversation from the Daily.co meeting, not mock data.

**Check participants:**
```bash
docker compose exec -T postgres psql -U reflector -d reflector -c \
  "SELECT participants FROM transcript ORDER BY created_at DESC LIMIT 1;" \
  | python3 -c "import sys, json; data=json.loads(sys.stdin.read()); print(json.dumps(data, indent=2))"
```

**Expected (REAL diarization):**
```json
[
  {
    "id": "<uuid>",
    "speaker": 0,
    "name": "Speaker 1"
  },
  {
    "id": "<uuid>",
    "speaker": 1,
    "name": "Speaker 2"
  }
]
```

**Note:** Speaker names will be generic ("Speaker 1", "Speaker 2", etc.) as determined by the diarization backend. Number of participants depends on how many actually spoke during the meeting.

**Check word-level data:**
```bash
docker compose exec -T postgres psql -U reflector -d reflector -c \
  "SELECT jsonb_array_length(topics->0->'words') as num_words_first_topic
   FROM transcript
   ORDER BY created_at DESC LIMIT 1;"
```

**Expected:**
```
num_words_first_topic: <varies based on actual conversation length and topic chunking>
```

**Verify speaker diarization in words:**
```bash
docker compose exec -T postgres psql -U reflector -d reflector -c \
  "SELECT
     topics->0->'words'->0->>'text' as first_word,
     topics->0->'words'->0->>'speaker' as speaker,
     topics->0->'words'->0->>'start' as start_time,
     topics->0->'words'->0->>'end' as end_time
   FROM transcript
   ORDER BY created_at DESC LIMIT 1;"
```

**Expected (REAL transcription):**
```
first_word: <actual first word from transcription>
speaker: 0, 1, 2, ... (actual speaker ID from diarization)
start_time: <actual timestamp in seconds>
end_time: <actual end timestamp>
```

**Note:** All timestamps and speaker IDs are from real transcription/diarization, synchronized across tracks.

---

## Test 8: Recording Type Verification

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
- [x] **Database recording entry created** with correct S3 path and status `completed`
- [ ] **Database transcript entry created** with status `uploaded`
- [ ] **Audio file downloaded** to `data/{transcript_id}/upload.webm`
- [ ] **Transcript has REAL data**: AI-generated title based on conversation
- [ ] **Transcript has topics** generated from actual content
- [ ] **Transcript has participants** with proper speaker diarization
- [ ] **Topics contain word-level data** with accurate timestamps and speaker IDs
- [ ] **Total duration** matches actual meeting length
- [ ] **MP3 and waveform files generated** by file processing pipeline
- [ ] **Frontend transcript page loads** without "Failed to load audio" error
- [ ] **Audio player functional** with working playback and waveform visualization
- [ ] **Multitrack processing completed** without errors in worker logs
- [ ] **Modal GPU backends accessible** (transcription and diarization)
