---
sidebar_position: 6
title: Daily.co Setup
---

# Daily.co Setup

This page covers Daily.co video platform setup for live meeting rooms. For the complete deployment guide, see [Deployment Guide](./overview).

Daily.co enables live video meetings with automatic recording and transcription.

## What You'll Set Up

```
User joins meeting → Daily.co video room → Recording to S3 → [Webhook] → Reflector transcribes
```

## Prerequisites

- [ ] **Daily.co account** - Free tier at https://dashboard.daily.co
- [ ] **AWS account** - For S3 storage
- [ ] **Reflector deployed** - Complete steps from [Deployment Guide](./overview)

---

## Create Daily.co Account

1. Visit https://dashboard.daily.co and sign up
2. Verify your email
3. Note your subdomain (e.g., `yourname.daily.co` → subdomain is `yourname`)

---

## Get Daily.co API Key

1. In Daily.co dashboard, go to **Developers**
2. Click **API Keys**
3. Click **Create API Key**
4. Copy the key (starts with a long string)

Save this for later.

---

## Create AWS S3 Bucket

Daily.co needs somewhere to store recordings before Reflector processes them.

```bash
# Choose a unique bucket name
BUCKET_NAME="reflector-dailyco-yourname" # -yourname is not a requirement, you can name the bucket as you wish
AWS_REGION="us-east-1"

# Create bucket
aws s3 mb s3://$BUCKET_NAME --region $AWS_REGION

# Enable versioning (required)
aws s3api put-bucket-versioning \
  --bucket $BUCKET_NAME \
  --versioning-configuration Status=Enabled
```

---

## Create IAM Role for Daily.co

Daily.co needs permission to write recordings to your S3 bucket.

Follow the guide https://docs.daily.co/guides/products/live-streaming-recording/storing-recordings-in-a-custom-s3-bucket

Save the role ARN - you'll need it soon.

It looks like: `arn:aws:iam::123456789012:role/DailyCo`

Shortly, you'll need to set up a role and give this role your s3 bucket access

No additional setup is required from Daily.co settings website side: the app code takes care of letting Daily know where to save the recordings.

---

## Configure Reflector

**Location: Reflector server**

Add to `server/.env`:

```env
# Daily.co Configuration
DEFAULT_VIDEO_PLATFORM=daily
DAILY_API_KEY=<your-api-key-from-daily-setup>
DAILY_SUBDOMAIN=<your-subdomain-from-daily-setup>

# S3 Storage for Daily.co recordings
DAILYCO_STORAGE_AWS_BUCKET_NAME=<your-bucket-from-daily-setup>
DAILYCO_STORAGE_AWS_REGION=us-east-1
DAILYCO_STORAGE_AWS_ROLE_ARN=<your-role-arn-from-daily-setup>

# Transcript storage (required for Daily.co multitrack processing)
TRANSCRIPT_STORAGE_BACKEND=local
# Or use S3 for production:
# TRANSCRIPT_STORAGE_BACKEND=aws
# TRANSCRIPT_STORAGE_AWS_ACCESS_KEY_ID=<your-key>
# TRANSCRIPT_STORAGE_AWS_SECRET_ACCESS_KEY=<your-secret>
# TRANSCRIPT_STORAGE_AWS_BUCKET_NAME=<your-bucket-name>
# TRANSCRIPT_STORAGE_AWS_REGION=<your-bucket-region>
```

---

## Restart Services

After changing `.env` files, reload with `up -d`:

```bash
sudo docker compose -f docker-compose.prod.yml up -d server worker
```

**Note**: `docker compose up -d` detects env changes and recreates containers automatically.

---

## Test Live Room

1. Visit your Reflector frontend: `https://app.example.com`
2. Go to **Rooms**
3. Create or join a room
4. Allow camera/microphone access
5. You should see Daily.co video interface
6. Speak for 10-20 seconds
7. Leave the meeting
8. Recording should appear in **Transcripts** within 5 minutes

---

## Troubleshooting

### Recording doesn't appear in S3

1. Check Daily.co dashboard → **Logs** for errors
2. Verify IAM role trust policy has correct Daily.co account ID and your Daily.co subdomain
3. Verify that the bucket has

### Recording in S3 but not transcribed

1. Check webhook is configured (Reflector should auto-create it)
2. Check worker logs:
   ```bash
   docker compose -f docker-compose.prod.yml logs worker --tail 50
   ```
3. Verify `DAILYCO_STORAGE_AWS_*` vars in `server/.env`

### "Access Denied" when Daily.co tries to write to S3

1. Double-check IAM role ARN in Daily.co settings
2. Verify bucket name matches exactly
3. Check IAM policy has `s3:PutObject` permission

---

## Webhook Configuration [optional]

`manage_daily_webhook.py` script guides you through creating a webhook for Daily recordings.

The webhook isn't required - polling mechanism is the default and performed automatically.

This guide won't go deep into webhook setup.
