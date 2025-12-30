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
- **Virtual Meeting Rooms**: Whereby and Daily.co integration
- **Team Collaboration**: Share transcripts with team
- **Persistent Storage**: Long-term transcript archive
- **Meeting History**: Search and browse past transcripts
- **Custom Integration**: Webhooks and API access
- **User Management**: Role-based access control

### Authentication Options

#### Authentik Integration
Enterprise-grade SSO with support for:
- SAML 2.0
- OAuth 2.0 / OIDC
- LDAP / Active Directory
- Multi-factor authentication

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
| Meeting History | ❌ | ✅ |
| Webhooks | ❌ | ✅ |

## Security Considerations

### Public Mode Security
- File size restrictions
- Automatic cleanup of old data

### Private Mode Security
- Audit logging
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
- You want searchable meeting history
