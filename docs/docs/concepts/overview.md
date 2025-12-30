---
sidebar_position: 1
title: Architecture Overview
---

# Architecture Overview

Reflector is built as a modern, scalable, microservices-based application designed to handle audio processing workloads efficiently while maintaining data privacy and control.

## System Components

### Frontend Application

The user interface is built with **Next.js 14** using the App Router pattern, providing:

- Server-side rendering for optimal performance
- Real-time WebSocket connections for live transcription
- WebRTC support for audio streaming and live meetings (via Daily.co or Whereby)
- Responsive design with Chakra UI components

### Backend API Server

The core API is powered by **FastAPI**, a modern Python framework that provides:

- High-performance async request handling
- Automatic OpenAPI documentation generation
- Type safety with Pydantic models
- WebSocket support for real-time updates

### Processing Pipeline

Audio processing is handled through a modular pipeline architecture:

```
Audio Input → Chunking → Transcription → Diarization → Post-Processing → Storage
```

Each step can run independently and in parallel, allowing for:
- Scalable processing of large files
- Real-time streaming capabilities
- Fault tolerance and retry mechanisms

### Worker Architecture

Background tasks are managed by **Celery** workers with **Redis** as the message broker:

- Distributed task processing
- Priority queues for time-sensitive operations
- Automatic retry on failure
- Progress tracking and notifications

### GPU Acceleration

ML models run on GPU-accelerated infrastructure:

- **Modal.com** for serverless GPU processing
- **Self-hosted GPU** with Docker deployment
- Automatic scaling based on demand
- Cost-effective pay-per-use model

## Data Flow

### Daily.co Meeting Recording Flow

1. **Recording**: Daily.co captures separate audio tracks per participant
2. **Webhook**: Daily.co notifies Reflector when recording is ready
3. **Track Download**: Individual participant tracks fetched from S3
4. **Padding**: Tracks padded with silence based on join time for synchronization
5. **Transcription**: Each track transcribed independently (speaker = track index)
6. **Merge**: Transcriptions sorted by timestamp and combined
7. **Mixdown**: Tracks mixed to single MP3 for playback
8. **Post-Processing**: Topics, title, and summaries generated via LLM
9. **Delivery**: Results stored and user notified via WebSocket

### File Upload Flow

1. **Upload**: User uploads audio file through web interface
2. **Storage**: File stored temporarily
3. **Transcription**: Full file transcribed via Whisper
4. **Diarization**: ML-based speaker identification (Pyannote)
5. **Post-Processing**: Topics, title, summaries
6. **Delivery**: Results stored and user notified

### Live Streaming Flow

1. **WebRTC Connection**: Browser establishes peer connection via Daily.co or Whereby
2. **Audio Capture**: Microphone audio streamed to server
3. **Buffering**: Audio buffered for processing
4. **Real-time Processing**: Segments transcribed as they arrive
5. **WebSocket Updates**: Results streamed back to client
6. **Continuous Assembly**: Full transcript built progressively

## Deployment Architecture

### Container-Based Deployment

All components are containerized for consistent deployment:

```yaml
services:
  frontend:    # Next.js application
  backend:     # FastAPI server
  worker:      # Celery workers
  redis:       # Message broker
  postgres:    # Database
  caddy:       # Reverse proxy
```

### Networking

- **Host Network Mode**: Required for WebRTC/ICE compatibility
- **Caddy Reverse Proxy**: Handles SSL termination and routing
- **WebSocket Upgrade**: Supports real-time connections

## Scalability Considerations

### Horizontal Scaling

- **Stateless Backend**: Multiple API server instances
- **Worker Pools**: Add workers based on queue depth
- **Database Pooling**: Connection management for concurrent access

### Vertical Scaling

- **GPU Workers**: Scale up for faster model inference
- **Memory Optimization**: Efficient audio buffering

## Security Architecture

### Authentication & Authorization

- **JWT Tokens**: Stateless authentication
- **Authentik Integration**: Enterprise SSO support
- **Role-Based Access**: Granular permissions

### Data Protection

- **Encryption in Transit**: TLS for all connections
- **Temporary Storage**: Automatic cleanup of processed files

### Privacy by Design

- **Local Processing**: Option to process entirely on-premises
- **No Training on User Data**: Models are pre-trained
- **Data Isolation**: Multi-tenant data separation

## Integration Points

### External Services

- **Modal.com**: GPU processing
- **AWS S3**: Long-term storage
- **Whereby**: Video conferencing rooms
- **Zulip**: Chat integration (optional)

### APIs and Webhooks

- **RESTful API**: Standard CRUD operations
- **WebSocket API**: Real-time updates
- **Webhook Notifications**: Processing completion events
- **OpenAPI Specification**: Machine-readable API definition

## Performance Optimization

### Caching Strategy

- **Redis Cache**: Frequently accessed data
- **CDN**: Static asset delivery
- **Browser Cache**: Client-side optimization

### Database Optimization

- **Indexed Queries**: Fast search and retrieval
- **Connection Pooling**: Efficient resource usage
- **Query Optimization**: N+1 query prevention

### Processing Optimization

- **Batch Processing**: Efficient GPU utilization
- **Parallel Execution**: Multi-core CPU usage
- **Stream Processing**: Reduced memory footprint

## Monitoring and Observability

### Metrics Collection

- **Application Metrics**: Request rates, response times
- **System Metrics**: CPU, memory, disk usage
- **Business Metrics**: Transcription accuracy, processing times

### Logging

- **Structured Logging**: JSON format for analysis
- **Log Aggregation**: Centralized log management
- **Error Tracking**: Sentry integration

### Health Checks

- **Liveness Probes**: Component availability
- **Readiness Probes**: Service readiness
- **Dependency Checks**: External service status