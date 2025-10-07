import express from 'express';
import Redis from 'ioredis';
import cors from 'cors';

const app = express();
app.use(express.json());
app.use(cors());

// Initialize Redis client
const redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');

// Event logging
const LOG_EVENTS = process.env.ENABLE_EVENT_LOGGING === 'true';

interface UnifiedEvent {
  source: 'prosody' | 'jibri' | 'jicofo' | 'web' | 'client';
  type: string;
  timestamp: string;
  roomName: string;
  data: any;
  metadata?: {
    participantCount?: number;
    recordingId?: string;
    sessionId?: string;
  };
}

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Prosody webhook endpoint (room events)
app.post('/webhook/prosody', async (req, res) => {
  if (LOG_EVENTS) console.log('📥 Prosody event:', req.body);

  const event: UnifiedEvent = {
    source: 'prosody',
    type: req.body.event_type,
    timestamp: new Date().toISOString(),
    roomName: req.body.room_name || 'unknown',
    data: req.body,
    metadata: {
      participantCount: req.body.participant_count,
      sessionId: req.body.session_id,
    }
  };

  await publishEvent(event);
  res.json({ success: true });
});

// Jibri webhook endpoint (recording events)
app.post('/webhook/jibri', async (req, res) => {
  if (LOG_EVENTS) console.log('🎥 Jibri event:', req.body);

  const event: UnifiedEvent = req.body;

  await publishEvent(event);

  // Log recording completion
  if (event.type === 'recording_stopped') {
    console.log(`✅ Recording completed for room: ${event.roomName}`);
    console.log(`   Recording ID: ${event.metadata?.recordingId}`);
    console.log(`   Path: ${req.body.recording_path}`);
    await triggerRecordingProcessing(event);
  }

  res.json({ success: true });
});

// Client event endpoint (from frontend)
app.post('/webhook/client', async (req, res) => {
  if (LOG_EVENTS) console.log('💻 Client event:', req.body);

  const event: UnifiedEvent = {
    source: 'client',
    type: req.body.type,
    timestamp: new Date().toISOString(),
    roomName: req.body.roomName || 'unknown',
    data: req.body.data || {},
    metadata: req.body.metadata
  };

  await publishEvent(event);
  res.json({ success: true });
});

// Get events for a room
app.get('/events/:roomName', async (req, res) => {
  const roomName = req.params.roomName;
  const events = await redis.lrange(`jitsi:events:${roomName}`, 0, -1);

  res.json({
    roomName,
    events: events.map(e => JSON.parse(e)).reverse(),
    count: events.length
  });
});

// Get all recent events
app.get('/events', async (req, res) => {
  const keys = await redis.keys('jitsi:events:*');
  const allEvents = [];

  for (const key of keys) {
    const events = await redis.lrange(key, 0, 10);
    allEvents.push(...events.map(e => JSON.parse(e)));
  }

  res.json({
    events: allEvents.sort((a, b) =>
      new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    ),
    count: allEvents.length
  });
});

async function publishEvent(event: UnifiedEvent) {
  if (LOG_EVENTS) {
    console.log(`📡 Publishing event: ${event.type} for room: ${event.roomName}`);
  }

  try {
    // Publish to Redis pub/sub for real-time consumers
    await redis.publish('jitsi:events', JSON.stringify(event));

    // Store in Redis list for durability (keep last 100 events per room)
    const key = `jitsi:events:${event.roomName}`;
    await redis.lpush(key, JSON.stringify(event));
    await redis.ltrim(key, 0, 99);

    // Set expiry on room events (24 hours)
    await redis.expire(key, 86400);

    // Forward critical events to Reflector
    if (shouldForwardToReflector(event)) {
      await forwardToReflector(event);
    }
  } catch (error) {
    console.error('Failed to publish event:', error);
  }
}

function shouldForwardToReflector(event: UnifiedEvent): boolean {
  const criticalEvents = [
    'room_created',
    'room_destroyed',
    'participant_joined',
    'participant_left',
    'recording_started',
    'recording_stopped',
    'recording_failed',
    'videoConferenceJoined',
    'videoConferenceLeft'
  ];
  return criticalEvents.includes(event.type);
}

async function forwardToReflector(event: UnifiedEvent) {
  const reflectorUrl = process.env.REFLECTOR_WEBHOOK_URL;
  if (!reflectorUrl) {
    if (LOG_EVENTS) console.log('⚠️  No REFLECTOR_WEBHOOK_URL configured');
    return;
  }

  try {
    if (LOG_EVENTS) console.log(`➡️  Forwarding to Reflector: ${event.type}`);

    const response = await fetch(reflectorUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(event)
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
  } catch (error) {
    console.error('Failed to forward event to Reflector:', error);
    // Queue for retry
    await redis.lpush('jitsi:events:failed', JSON.stringify(event));
  }
}

async function triggerRecordingProcessing(event: UnifiedEvent) {
  const reflectorUrl = process.env.REFLECTOR_WEBHOOK_URL;
  if (!reflectorUrl) return;

  const processingRequest = {
    type: 'process_recording',
    recording_path: event.data.recording_path,
    room_name: event.roomName,
    session_id: event.metadata?.sessionId,
    recording_id: event.metadata?.recordingId,
    timestamp: event.timestamp
  };

  try {
    console.log('🔄 Triggering recording processing in Reflector');
    await fetch(`${reflectorUrl}/process`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(processingRequest)
    });
  } catch (error) {
    console.error('Failed to trigger recording processing:', error);
  }
}

const PORT = process.env.PORT || 3002;

redis.on('connect', () => {
  console.log('✅ Connected to Redis');
});

redis.on('error', (err) => {
  console.error('❌ Redis error:', err);
});

app.listen(PORT, () => {
  console.log(`🚀 Event collector listening on port ${PORT}`);
  console.log(`   Redis: ${process.env.REDIS_URL || 'redis://localhost:6379'}`);
  console.log(`   Reflector: ${process.env.REFLECTOR_WEBHOOK_URL || 'Not configured'}`);
  console.log(`   Event logging: ${LOG_EVENTS ? 'Enabled' : 'Disabled'}`);
});