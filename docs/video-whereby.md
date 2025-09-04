# Whereby Integration Configuration Guide

This guide explains how to configure Reflector to use Whereby as your video meeting platform for room creation, recording, and participant tracking.

## Overview

Whereby is a browser-based video meeting platform that provides hosted meeting rooms with recording capabilities. Reflector integrates with Whereby's API to:

- Create secure meeting rooms with custom branding
- Handle participant join/leave events via webhooks
- Automatically record meetings to AWS S3 storage
- Track meeting sessions and participant counts

## Requirements

### Whereby Account Setup

1. **Whereby Account**: Sign up for a Whereby business account at [whereby.com](https://whereby.com/business)
2. **API Access**: Request API access from Whereby support (required for programmatic room creation)
3. **Webhook Configuration**: Configure webhooks in your Whereby dashboard to point to your Reflector instance

### AWS S3 Storage

Whereby requires AWS S3 for recording storage. You need:
- AWS account with S3 access
- Dedicated S3 bucket for Whereby recordings
- AWS IAM credentials with S3 write permissions

## Configuration Variables

Add the following environment variables to your Reflector `.env` file:

### Required Variables

```bash
# Whereby API Configuration
WHEREBY_API_KEY=your-whereby-jwt-api-key
WHEREBY_WEBHOOK_SECRET=your-webhook-secret-from-whereby

# AWS S3 Storage for Recordings
AWS_WHEREBY_ACCESS_KEY_ID=your-aws-access-key
AWS_WHEREBY_ACCESS_KEY_SECRET=your-aws-secret-key
RECORDING_STORAGE_AWS_BUCKET_NAME=your-s3-bucket-name
```

### Optional Variables

```bash
# Whereby API URL (defaults to production)
WHEREBY_API_URL=https://api.whereby.dev/v1

# SQS Configuration (for recording processing)
AWS_PROCESS_RECORDING_QUEUE_URL=https://sqs.region.amazonaws.com/account/queue
SQS_POLLING_TIMEOUT_SECONDS=60
```

## Configuration Steps

### 1. Whereby API Key Setup

1. **Contact Whereby Support** to request API access for your account
2. **Generate JWT Token** in your Whereby dashboard under API settings
3. **Copy the JWT token** and set it as `WHEREBY_API_KEY` in your environment

The API key is a JWT token that looks like:
```
eyJ[...truncated JWT token...]
```

### 2. Webhook Configuration

1. **Access Whereby Dashboard** and navigate to webhook settings
2. **Set Webhook URL** to your Reflector instance:
   ```
   https://your-reflector-domain.com/v1/whereby
   ```
3. **Configure Events** to send the following event types:
   - `room.client.joined` - When participants join
   - `room.client.left` - When participants leave
4. **Generate Webhook Secret** and set it as `WHEREBY_WEBHOOK_SECRET`
5. **Save Configuration** in your Whereby dashboard

### 3. AWS S3 Storage Setup

1. **Create S3 Bucket** dedicated for Whereby recordings
2. **Create IAM User** with programmatic access
3. **Attach S3 Policy** with the following permissions:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "s3:PutObject",
           "s3:PutObjectAcl",
           "s3:GetObject"
         ],
         "Resource": "arn:aws:s3:::your-bucket-name/*"
       }
     ]
   }
   ```
4. **Configure Environment Variables** with the IAM credentials

### 4. Room Configuration

When creating rooms in Reflector, set the platform to use Whereby:

```bash
curl -X POST "https://your-reflector-domain.com/v1/rooms" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "name": "my-whereby-room",
    "platform": "whereby",
    "recording_type": "cloud",
    "recording_trigger": "automatic-2nd-participant",
    "is_locked": false,
    "room_mode": "normal"
  }'
```

## Meeting Features

### Recording Options

Whereby supports three recording types:
- **`none`**: No recording
- **`local`**: Local recording (not recommended for production)
- **`cloud`**: Cloud recording to S3 (recommended)

### Recording Triggers

Control when recordings start:
- **`none`**: No automatic recording
- **`prompt`**: Prompt users to start recording
- **`automatic`**: Start immediately when meeting begins
- **`automatic-2nd-participant`**: Start when second participant joins

### Room Modes

- **`normal`**: Standard meeting room
- **`group`**: Group meeting with advanced features

## Webhook Event Handling

Reflector automatically handles these Whereby webhook events:

### Participant Tracking
```json
{
  "type": "room.client.joined",
  "data": {
    "meetingId": "room-uuid",
    "numClients": 2
  }
}
```

### Recording Events
Whereby sends recording completion events that trigger Reflector's processing pipeline:
- Audio transcription
- Speaker diarization
- Summary generation

## Troubleshooting

### Common Issues

#### API Authentication Errors
**Symptoms**: 401 Unauthorized errors when creating meetings

**Solutions**:
1. Verify your `WHEREBY_API_KEY` is correct and not expired
2. Ensure you have API access enabled on your Whereby account
3. Contact Whereby support if API access is not available

#### Webhook Signature Validation Failed
**Symptoms**: Webhook events rejected with 401 errors

**Solutions**:
1. Verify `WHEREBY_WEBHOOK_SECRET` matches your Whereby dashboard configuration
2. Check webhook URL is correctly configured in Whereby dashboard
3. Ensure webhook endpoint is accessible from Whereby servers

#### Recording Upload Failures
**Symptoms**: Recordings not appearing in S3 bucket

**Solutions**:
1. Verify AWS credentials have S3 write permissions
2. Check S3 bucket name is correct and accessible
3. Ensure AWS region settings match your bucket location
4. Review AWS CloudTrail logs for permission issues

#### Participant Count Not Updating
**Symptoms**: Meeting participant counts remain at 0

**Solutions**:
1. Verify webhook events are being received at `/v1/whereby`
2. Check webhook signature validation is passing
3. Ensure meeting IDs match between Whereby and Reflector database

### Debug Commands

```bash
# Test Whereby API connectivity
curl -H "Authorization: Bearer $WHEREBY_API_KEY" \
  https://api.whereby.dev/v1/meetings

# Check webhook endpoint health
curl https://your-reflector-domain.com/v1/whereby/health

# Verify S3 bucket access
aws s3 ls s3://your-bucket-name --profile whereby-user
```

## Security Considerations

### API Key Security
- Store API keys securely using environment variables
- Rotate API keys regularly
- Never commit API keys to version control
- Use separate keys for development and production

### Webhook Security
- Always validate webhook signatures using HMAC-SHA256
- Use HTTPS for all webhook endpoints
- Implement rate limiting on webhook endpoints
- Monitor webhook events for suspicious activity

### Recording Privacy
- Ensure S3 bucket access is restricted to authorized users
- Consider encryption at rest for sensitive recordings
- Implement retention policies for recorded content
- Comply with data protection regulations (GDPR, etc.)

## Performance Optimization

### Meeting Scaling
- Monitor concurrent meeting limits on your Whereby plan
- Implement meeting cleanup for expired sessions
- Use appropriate room modes for different use cases

### Recording Processing
- Configure SQS for asynchronous recording processing
- Monitor S3 storage usage and costs
- Implement automatic cleanup of processed recordings

### Webhook Reliability
- Implement webhook retry mechanisms
- Monitor webhook delivery success rates
- Log webhook events for debugging and auditing

## Migration from Other Platforms

If migrating from another video platform:

1. **Update Room Configuration**: Change existing rooms to use `"platform": "whereby"`
2. **Configure Webhooks**: Set up Whereby webhook endpoints
3. **Test Integration**: Verify meeting creation and event handling
4. **Monitor Performance**: Watch for any issues during transition
5. **Update Documentation**: Inform users of any workflow changes

## Support

For Whereby-specific issues:
- **Whereby Support**: [whereby.com/support](https://whereby.com/support)
- **API Documentation**: [whereby.dev](https://whereby.dev)
- **Status Page**: [status.whereby.com](https://status.whereby.com)

For Reflector integration issues:
- Check application logs for error details
- Verify environment variable configuration
- Test webhook connectivity and authentication
- Review AWS permissions and S3 access