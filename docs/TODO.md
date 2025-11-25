# Documentation TODO List

This file tracks information needed from the user to complete the documentation.

## Required Information

### Processing Times & Costs

Please provide actual numbers for:

- [ ] **Modal.com GPU Costs**
  - Cost per hour of audio for Whisper transcription
  - Cost per hour of audio for Pyannote diarization
  - Cost per hour of audio for Seamless-M4T translation
  - Typical GPU instance used (T4, A10, etc.)

- [ ] **RunPod LLM Costs**
  - Cost per 1000 tokens for summarization
  - Model used (phi-4-unsloth-bnb-4bit)
  - RTX 4000 Ada instance cost per hour

- [ ] **AWS S3 Storage**
  - Cost per GB per month
  - Data transfer costs
  - Typical storage requirements per hour of audio

- [ ] **Whereby API**
  - Monthly cost structure
  - API call limits
  - Room participant limits

- [ ] **Actual Processing Times**
  - Whisper tiny model: X minutes per hour of audio
  - Whisper base model: X minutes per hour of audio
  - Whisper large-v3 model: X minutes per hour of audio
  - Diarization: X minutes per hour of audio
  - Translation: X minutes per hour of audio

### Screenshots Needed

Location: `/docs/static/screenshots/`

Please provide screenshots of:

- [ ] **Dashboard Overview** - Main dashboard showing recent transcripts
- [ ] **Live Transcription** - Active transcription in progress
- [ ] **Meeting Room Interface** - Whereby room with participants
- [ ] **Transcript with Diarization** - Showing speaker labels
- [ ] **Settings Page** - Configuration options
- [ ] **API Documentation** - OpenAPI/Swagger interface
- [ ] **File Upload Interface** - Drag and drop upload
- [ ] **Translation View** - Showing original and translated text
- [ ] **Summary View** - Generated summary and topics

### Setup Screenshots

Please provide step-by-step screenshots for:

- [ ] **Modal.com Setup**
  - Creating account
  - Getting API keys
  - Deploying functions

- [ ] **Whereby Configuration**
  - Creating developer account
  - Getting API credentials
  - Setting up rooms

- [ ] **AWS S3 Setup**
  - Creating bucket
  - Setting permissions
  - Getting access keys

- [ ] **Authentik Integration**
  - Adding application
  - Configuring OAuth
  - Setting up users

### Technical Details

Please provide specific values for:

- [ ] **WebRTC Configuration**
  - Exact UDP port range used (e.g., 10000-20000)
  - STUN server configuration (if any)
  - ICE candidate gathering timeout

- [ ] **Worker Configuration**
  - Default Celery worker count
  - Worker memory limits
  - Queue priorities

- [ ] **Redis Requirements**
  - Typical memory usage
  - Persistence configuration
  - Eviction policies

- [ ] **PostgreSQL**
  - Expected database growth (MB per hour of audio)
  - Recommended connection pool size
  - Backup strategy

- [ ] **Performance Metrics**
  - Average transcription accuracy (WER)
  - Average diarization accuracy (DER)
  - Translation quality scores
  - Typical latency for live streaming

### Configuration Examples

Please provide real-world examples for:

- [ ] **Production .env file** (sanitized)
- [ ] **Caddy configuration** for production
- [ ] **Docker compose** for production deployment
- [ ] **Nginx configuration** (if alternative to Caddy)

### API Examples

Please provide:

- [ ] **Sample API requests** for common operations
- [ ] **WebSocket message examples**
- [ ] **Webhook payload examples**
- [ ] **Error response examples**

## How to Add Information

1. **For text information**: Edit the relevant markdown files in `/docs/docs/`
2. **For screenshots**: Add to `/docs/static/screenshots/` and reference in docs
3. **For code examples**: Add to documentation with proper syntax highlighting

## Priority Items

High priority (blocks documentation completeness):
1. Modal.com costs and setup steps
2. Basic screenshots (dashboard, transcription)
3. Docker deployment configuration

Medium priority (enhances documentation):
1. Performance metrics
2. Advanced configuration examples
3. Troubleshooting scenarios

Low priority (nice to have):
1. Video tutorials
2. Architecture diagrams
3. Benchmark comparisons

## Documentation Structure

Once information is provided, update these files:
- `/docs/docs/installation/modal-setup.md` - Add Modal.com setup screenshots
- `/docs/docs/installation/whereby-setup.md` - Add Whereby configuration steps
- `/docs/docs/reference/configuration.md` - Add environment variable details
- `/docs/docs/pipelines/file-pipeline.md` - Add actual processing times
- `/docs/docs/pipelines/live-pipeline.md` - Add latency measurements

## Notes

- Replace placeholder values with actual data
- Ensure all sensitive information is sanitized
- Test all configuration examples before documenting
- Verify all costs are up-to-date

---

Last updated: 2025-08-20
Contact: [Your Email]