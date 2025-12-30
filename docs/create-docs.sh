#!/bin/bash

# Create directory structure
mkdir -p docs/concepts
mkdir -p docs/installation
mkdir -p docs/pipelines
mkdir -p docs/reference/architecture
mkdir -p docs/reference/processors
mkdir -p docs/reference/api

# Create all documentation files with content
echo "Creating documentation files..."

# Concepts - Modes
cat > docs/concepts/modes.md << 'EOF'
---
sidebar_position: 2
title: Operating Modes
---

# Operating Modes

Reflector operates in two distinct modes to accommodate different use cases and security requirements.

## Public Mode

Public mode provides immediate access to core transcription features without requiring authentication.

### Features Available
- **File Upload**: Process audio files up to 2GB
- **Live Transcription**: Stream audio from microphone
- **Basic Processing**: Transcription and diarization
- **Temporary Storage**: Results available for 24 hours

### Limitations
- No persistent storage
- No meeting rooms
- Limited to single-user sessions
- No team collaboration features

### Use Cases
- Quick transcription needs
- Testing and evaluation
- Individual users
- Public demonstrations

## Private Mode

Private mode unlocks the full potential of Reflector with authentication and persistent storage.

### Additional Features
- **Virtual Meeting Rooms**: Whereby integration
- **Team Collaboration**: Share transcripts with team
- **Persistent Storage**: Long-term transcript archive
- **Advanced Analytics**: Meeting insights and trends
- **Custom Integration**: Webhooks and API access
- **User Management**: Role-based access control

### Authentication Options

#### Authentik Integration
Enterprise-grade SSO with support for:
- SAML 2.0
- OAuth 2.0 / OIDC
- LDAP / Active Directory
- Multi-factor authentication

#### JWT Authentication
Stateless token-based auth for:
- API access
- Service-to-service communication
- Mobile applications

### Room Management

Virtual rooms provide dedicated spaces for meetings:
- **Persistent URLs**: Same link for recurring meetings
- **Access Control**: Invite-only or open rooms
- **Recording Consent**: Automatic consent management
- **Custom Settings**: Per-room configuration

## Mode Selection

The mode is determined by your deployment configuration:

```yaml
# Public Mode (no authentication)
REFLECTOR_AUTH_BACKEND=none

# Private Mode (with authentication)
REFLECTOR_AUTH_BACKEND=jwt
# or
REFLECTOR_AUTH_BACKEND=authentik
```

## Feature Comparison

| Feature | Public Mode | Private Mode |
|---------|------------|--------------|
| File Upload | ✅ | ✅ |
| Live Transcription | ✅ | ✅ |
| Speaker Diarization | ✅ | ✅ |
| Translation | ✅ | ✅ |
| Summarization | ✅ | ✅ |
| Meeting Rooms | ❌ | ✅ |
| Persistent Storage | ❌ | ✅ |
| Team Collaboration | ❌ | ✅ |
| API Access | Limited | Full |
| User Management | ❌ | ✅ |
| Custom Branding | ❌ | ✅ |
| Analytics | ❌ | ✅ |
| Webhooks | ❌ | ✅ |

## Security Considerations

### Public Mode Security
- Rate limiting to prevent abuse
- File size restrictions
- Automatic cleanup of old data
- No PII storage

### Private Mode Security
- Encrypted data storage
- Audit logging
- Session management
- Access control lists
- Data retention policies

## Choosing the Right Mode

### Choose Public Mode if:
- You need quick, one-time transcriptions
- You're evaluating Reflector
- You don't need persistent storage
- You're processing non-sensitive content

### Choose Private Mode if:
- You need team collaboration
- You require persistent storage
- You're processing sensitive content
- You need meeting room functionality
- You want advanced analytics
EOF

# Concepts - Independence
cat > docs/concepts/independence.md << 'EOF'
---
sidebar_position: 3
title: Data Independence
---

# Data Independence & Privacy

Reflector is designed with privacy and data independence as core principles, giving you complete control over your data and processing.

## Privacy by Design

### No Third-Party Data Sharing

Your audio and transcripts are never shared with third parties:
- **Local Processing**: All ML models can run on your infrastructure
- **No Training on User Data**: Your content is never used to improve models
- **Isolated Processing**: Each transcript is processed in isolation
- **No Analytics Tracking**: No usage analytics sent to external services

### Data Ownership

You maintain complete ownership of all data:
- **Export Anytime**: Download all your transcripts and audio
- **Delete on Demand**: Permanent deletion with no recovery
- **API Access**: Full programmatic access to your data
- **No Vendor Lock-in**: Standard formats for easy migration

## Processing Transparency

### What Happens to Your Audio

1. **Upload/Stream**: Audio received by your server
2. **Temporary Storage**: Stored only for processing duration
3. **Processing**: ML models process audio locally or on Modal
4. **Results Storage**: Transcripts stored in your database
5. **Cleanup**: Original audio deleted (unless configured otherwise)

### Local vs Cloud Processing

#### Local Processing
When configured for local processing:
- All models run on your hardware
- No data leaves your infrastructure
- Complete air-gap capability
- Higher hardware requirements

#### Modal.com Processing
When using Modal for GPU acceleration:
- Audio chunks sent to Modal for processing
- Processed immediately and deleted
- No long-term storage on Modal
- Modal's security: SOC 2 Type II compliant

### Data Retention

Default retention policies:
- **Public Mode**: 24 hours then automatic deletion
- **Private Mode**: Configurable (default: indefinite)
- **Audio Files**: Deleted after processing (configurable)
- **Transcripts**: Retained based on policy

## Compliance Features

### GDPR Compliance

- **Right to Access**: Export all user data
- **Right to Deletion**: Permanent data removal
- **Data Portability**: Standard export formats
- **Privacy by Default**: Minimal data collection

### HIPAA Considerations

For healthcare deployments:
- **Self-hosted Option**: Complete infrastructure control
- **Encryption**: At rest and in transit
- **Audit Logging**: Complete access trail
- **Access Controls**: Role-based permissions

### Industry Standards

- **TLS 1.3**: Modern encryption for data in transit
- **AES-256**: Encryption for data at rest
- **JWT Tokens**: Secure, stateless authentication
- **OWASP Guidelines**: Security best practices

## Self-Hosted Deployment

### Complete Independence

Self-hosting provides maximum control:
- **Your Infrastructure**: Run on your servers
- **Your Network**: No external connections required
- **Your Policies**: Implement custom retention
- **Your Compliance**: Meet specific requirements

### Air-Gap Capability

Reflector can run completely offline:
1. Download all models during setup
2. Configure for local processing only
3. Disable all external integrations
4. Run in isolated network environment

## Data Flow Control

### Configurable Processing

Control where each step happens:

```yaml
# All local processing
TRANSCRIPT_BACKEND=local
DIARIZATION_BACKEND=local
TRANSLATION_BACKEND=local

# Hybrid approach
TRANSCRIPT_BACKEND=modal  # Fast GPU processing
DIARIZATION_BACKEND=local # Sensitive speaker data
TRANSLATION_BACKEND=modal  # Non-sensitive translation
```

### Storage Options

Choose where data is stored:
- **Local Filesystem**: Complete control
- **PostgreSQL**: Self-hosted database
- **S3-Compatible**: MinIO or AWS with encryption
- **Hybrid**: Different storage for different data types

## Security Architecture

### Defense in Depth

Multiple layers of security:
1. **Network Security**: Firewalls and VPNs
2. **Application Security**: Input validation and sanitization
3. **Data Security**: Encryption and access controls
4. **Operational Security**: Logging and monitoring

### Zero Trust Principles

- **Verify Everything**: All requests authenticated
- **Least Privilege**: Minimal permissions granted
- **Assume Breach**: Design for compromise containment
- **Encrypt Everything**: No plaintext transmission

## Audit and Compliance

### Audit Logging

Comprehensive logging of:
- **Access Events**: Who accessed what and when
- **Processing Events**: What was processed and how
- **Configuration Changes**: System modifications
- **Security Events**: Failed authentication attempts

### Compliance Reporting

Generate reports for:
- **Data Processing**: What data was processed
- **Data Access**: Who accessed the data
- **Data Retention**: What was retained or deleted
- **Security Events**: Security-related incidents

## Best Practices

### For Maximum Privacy

1. **Self-host** all components
2. **Use local processing** for all models
3. **Implement short retention** periods
4. **Encrypt all storage** at rest
5. **Use VPN** for all connections
6. **Regular audits** of access logs

### For Balanced Approach

1. **Self-host core services** (database, API)
2. **Use Modal for processing** (faster, cost-effective)
3. **Implement encryption** everywhere
4. **Regular backups** with encryption
5. **Monitor access** patterns
EOF

# Concepts - Pipeline
cat > docs/concepts/pipeline.md << 'EOF'
---
sidebar_position: 4
title: Processing Pipeline
---

# Processing Pipeline

Reflector uses a sophisticated pipeline architecture to process audio efficiently and accurately.

## Pipeline Overview

The processing pipeline consists of modular components that can be combined and configured based on your needs:

```mermaid
graph LR
    A[Audio Input] --> B[Pre-processing]
    B --> C[Chunking]
    C --> D[Transcription]
    D --> E[Diarization]
    E --> F[Alignment]
    F --> G[Post-processing]
    G --> H[Output]
```

## Pipeline Components

### Audio Input

Accepts various input sources:
- **File Upload**: MP3, WAV, M4A, WebM, MP4
- **WebRTC Stream**: Live browser audio
- **Recording Integration**: Whereby recordings
- **API Upload**: Direct API submission

### Pre-processing

Prepares audio for optimal processing:
- **Format Conversion**: Convert to 16kHz mono WAV
- **Normalization**: Adjust volume to -23 LUFS
- **Noise Reduction**: Optional background noise removal
- **Validation**: Check duration and quality

### Chunking

Splits audio for parallel processing:
- **Fixed Size**: 30-second chunks by default
- **Overlap**: 1-second overlap for continuity
- **Smart Boundaries**: Attempt to split at silence
- **Metadata**: Track chunk positions

### Transcription

Converts speech to text:
- **Model Selection**: Whisper or Parakeet
- **Language Detection**: Automatic or specified
- **Timestamp Generation**: Word-level timing
- **Confidence Scores**: Quality indicators

### Diarization

Identifies different speakers:
- **Voice Activity Detection**: Find speech segments
- **Speaker Embedding**: Extract voice characteristics
- **Clustering**: Group similar voices
- **Label Assignment**: Assign speaker IDs

### Alignment

Merges all processing results:
- **Chunk Assembly**: Combine transcription chunks
- **Speaker Mapping**: Align speakers with text
- **Overlap Resolution**: Handle chunk boundaries
- **Timeline Creation**: Build unified timeline

### Post-processing

Enhances the final output:
- **Formatting**: Apply punctuation and capitalization
- **Translation**: Convert to target languages
- **Summarization**: Generate concise summaries
- **Topic Extraction**: Identify key themes
- **Action Items**: Extract tasks and decisions

## Processing Modes

### Batch Processing

For uploaded files:
- Optimized for throughput
- Parallel chunk processing
- Higher accuracy models
- Complete file analysis

### Stream Processing

For live audio:
- Optimized for latency
- Sequential processing
- Real-time feedback
- Progressive results

### Hybrid Processing

For meetings:
- Stream during meeting
- Batch after completion
- Best of both modes
- Maximum accuracy

## Pipeline Configuration

### Model Selection

Choose models based on requirements:

```python
# High accuracy (slower)
config = {
    "transcription_model": "whisper-large-v3",
    "diarization_model": "pyannote-3.1",
    "translation_model": "seamless-m4t-large"
}

# Balanced (default)
config = {
    "transcription_model": "whisper-base",
    "diarization_model": "pyannote-3.1",
    "translation_model": "seamless-m4t-medium"
}

# Fast processing
config = {
    "transcription_model": "whisper-tiny",
    "diarization_model": "pyannote-3.1-fast",
    "translation_model": "seamless-m4t-small"
}
```

### Processing Options

Customize pipeline behavior:

```yaml
# Parallel processing
max_parallel_chunks: 10
chunk_size_seconds: 30
chunk_overlap_seconds: 1

# Quality settings
enable_noise_reduction: true
enable_normalization: true
min_speech_confidence: 0.5

# Post-processing
enable_translation: true
target_languages: ["es", "fr", "de"]
enable_summarization: true
summary_length: "medium"
```

## Performance Characteristics

### Processing Times

For 1 hour of audio:

| Pipeline Config | Processing Time | Accuracy |
|----------------|-----------------|----------|
| Fast | 2-3 minutes | 85-90% |
| Balanced | 5-8 minutes | 92-95% |
| High Accuracy | 15-20 minutes | 95-98% |

### Resource Usage

| Component | CPU Usage | Memory | GPU |
|-----------|-----------|---------|-----|
| Transcription | Medium | 2-4 GB | Required |
| Diarization | High | 4-8 GB | Required |
| Translation | Low | 2-3 GB | Optional |
| Post-processing | Low | 1-2 GB | Not needed |

## Pipeline Orchestration

### Celery Task Chain

The pipeline is orchestrated using Celery:

```python
chain = (
    chunk_audio.s(audio_id) |
    group(transcribe_chunk.s(chunk) for chunk in chunks) |
    merge_transcriptions.s() |
    diarize_audio.s() |
    align_speakers.s() |
    post_process.s()
)
```

### Error Handling

Robust error recovery:
- **Automatic Retry**: Failed tasks retry up to 3 times
- **Partial Recovery**: Continue with successful chunks
- **Fallback Models**: Use alternative models on failure
- **Error Reporting**: Detailed error messages

### Progress Tracking

Real-time progress updates:
- **Chunk Progress**: Track individual chunk processing
- **Overall Progress**: Percentage completion
- **ETA Calculation**: Estimated completion time
- **WebSocket Updates**: Live progress to clients

## Optimization Strategies

### GPU Utilization

Maximize GPU efficiency:
- **Batch Processing**: Process multiple chunks together
- **Model Caching**: Keep models loaded in memory
- **Dynamic Batching**: Adjust batch size based on GPU memory
- **Multi-GPU Support**: Distribute across available GPUs

### Memory Management

Efficient memory usage:
- **Streaming Processing**: Process large files in chunks
- **Garbage Collection**: Clean up after each chunk
- **Memory Limits**: Prevent out-of-memory errors
- **Disk Caching**: Use disk for large intermediate results

### Network Optimization

Minimize network overhead:
- **Compression**: Compress audio before transfer
- **CDN Integration**: Use CDN for static assets
- **Connection Pooling**: Reuse network connections
- **Parallel Uploads**: Multiple concurrent uploads

## Quality Assurance

### Accuracy Metrics

Monitor processing quality:
- **Word Error Rate (WER)**: Transcription accuracy
- **Diarization Error Rate (DER)**: Speaker identification accuracy
- **Translation BLEU Score**: Translation quality
- **Summary Coherence**: Summary quality metrics

### Validation Steps

Ensure output quality:
- **Confidence Thresholds**: Filter low-confidence segments
- **Consistency Checks**: Verify timeline consistency
- **Language Validation**: Ensure correct language detection
- **Format Validation**: Check output format compliance

## Advanced Features

### Custom Models

Use your own models:
- **Fine-tuned Whisper**: Domain-specific models
- **Custom Diarization**: Trained on your speakers
- **Specialized Post-processing**: Industry-specific formatting

### Pipeline Extensions

Add custom processing steps:
- **Sentiment Analysis**: Analyze emotional tone
- **Entity Extraction**: Identify people, places, organizations
- **Custom Metrics**: Calculate domain-specific metrics
- **Integration Hooks**: Call external services
EOF

# Create installation documentation
cat > docs/installation/overview.md << 'EOF'
---
sidebar_position: 1
title: Installation Overview
---

# Installation Overview

Reflector is designed for self-hosted deployment, giving you complete control over your infrastructure and data.

## Deployment Options

### Docker Deployment (Recommended)

The easiest way to deploy Reflector:
- Pre-configured containers
- Automated dependency management
- Consistent environment
- Easy updates

### Manual Installation

For custom deployments:
- Greater control over configuration
- Integration with existing infrastructure
- Custom optimization options
- Development environments

## Requirements

### System Requirements

**Minimum Requirements:**
- CPU: 4 cores
- RAM: 8 GB
- Storage: 50 GB
- OS: Ubuntu 20.04+ or similar Linux

**Recommended Requirements:**
- CPU: 8+ cores
- RAM: 16 GB
- Storage: 100 GB SSD
- GPU: NVIDIA GPU with 8GB+ VRAM (for local processing)

### Network Requirements

- Public IP address (for WebRTC)
- Ports: 80, 443, 8000, 3000
- Domain name (for SSL)
- SSL certificate (Let's Encrypt supported)

## Required Services

### Core Services

These services are required for basic operation:

1. **PostgreSQL** - Primary database
2. **Redis** - Message broker and cache
3. **Docker** - Container runtime

### GPU Processing

Choose one:
- **Modal.com** - Serverless GPU (recommended)
- **Local GPU** - Self-hosted GPU processing

### Optional Services

Enhance functionality with:
- **AWS S3** - Long-term storage
- **Whereby** - Video conferencing rooms
- **Authentik** - Enterprise authentication
- **Zulip** - Chat integration

## Quick Start

### Using Docker Compose

1. Clone the repository:
```bash
git clone https://github.com/monadical-sas/reflector.git
cd reflector
```

2. Navigate to docker directory:
```bash
cd docker
```

3. Copy and configure environment:
```bash
cp .env.example .env
# Edit .env with your settings
```

4. Start services:
```bash
docker compose up -d
```

5. Access Reflector:
- Frontend: https://your-domain.com
- API: https://your-domain.com/api

## Configuration Overview

### Essential Configuration

```env
# Database
DATABASE_URL=postgresql://user:pass@localhost/reflector

# Redis
REDIS_URL=redis://localhost:6379

# Modal.com (for GPU processing)
TRANSCRIPT_MODAL_API_KEY=your-key
DIARIZATION_MODAL_API_KEY=your-key

# Domain
DOMAIN=your-domain.com
```

### Security Configuration

```env
# Authentication
REFLECTOR_AUTH_BACKEND=jwt
NEXTAUTH_SECRET=generate-strong-secret

# SSL (handled by Caddy)
# Automatic with Let's Encrypt
```

## Service Architecture

```mermaid
graph TD
    A[Caddy Reverse Proxy] --> B[Frontend - Next.js]
    A --> C[Backend - FastAPI]
    C --> D[PostgreSQL]
    C --> E[Redis]
    C --> F[Celery Workers]
    F --> G[Modal.com GPU]
```

## Next Steps

1. **Review Requirements**: [System Requirements](./requirements)
2. **Docker Setup**: [Docker Deployment Guide](./docker-setup)
3. **Configure Services**:
   - [Modal.com Setup](./modal-setup)
   - [Whereby Setup](./whereby-setup)
   - [AWS S3 Setup](./aws-setup)
4. **Optional Services**:
   - [Authentik Setup](./authentik-setup)
   - [Zulip Setup](./zulip-setup)

## Getting Help

- [Troubleshooting Guide](../reference/troubleshooting)
- [GitHub Issues](https://github.com/monadical-sas/reflector/issues)
- [Community Discord](#)
EOF

chmod +x create-docs.sh
echo "Documentation creation script ready. Run ./create-docs.sh to generate all docs."