---
sidebar_position: 6
title: Daily.co Setup
---

# Daily.co Setup

This page covers Daily.co video platform setup for live meeting rooms. For the complete deployment guide, see [Deployment Guide](./overview).

Daily.co enables live video meetings with automatic recording and transcription.

## What You'll Set Up

```
User joins meeting → Daily.co video room → Recording to S3 → Webhook → Reflector transcribes
```

## Prerequisites

- [ ] **Daily.co account** - Free tier at https://dashboard.daily.co
- [ ] **AWS account** - For S3 storage
- [ ] **Reflector deployed** - Complete Steps 1-7 from [Deployment Guide](./overview)

---

## Step 1: Create Daily.co Account

1. Visit https://dashboard.daily.co and sign up
2. Verify your email
3. Note your subdomain (e.g., `yourname.daily.co` → subdomain is `yourname`)

---

## Step 2: Get Daily.co API Key

1. In Daily.co dashboard, go to **Developers**
2. Click **API Keys**
3. Click **Create API Key**
4. Copy the key (starts with a long string)

Save this for Step 6.

---

## Step 3: Create AWS S3 Bucket

Daily.co needs somewhere to store recordings before Reflector processes them.

```bash
# Choose a unique bucket name
BUCKET_NAME="reflector-dailyco-yourname"
AWS_REGION="us-east-1"

# Create bucket
aws s3 mb s3://$BUCKET_NAME --region $AWS_REGION

# Enable versioning (optional but recommended)
aws s3api put-bucket-versioning \
  --bucket $BUCKET_NAME \
  --versioning-configuration Status=Enabled
```

---

## Step 4: Create IAM Role for Daily.co

Daily.co needs permission to write recordings to your S3 bucket.

### Create Trust Policy

Create `daily-trust-policy.json`:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::741088605061:root"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "daily-co"
        }
      }
    }
  ]
}
```

**Note**: `741088605061` is Daily.co's AWS account ID (this is public and correct).

### Create the Role

```bash
aws iam create-role \
  --role-name DailyCo \
  --assume-role-policy-document file://daily-trust-policy.json
```

### Create Permission Policy

Create `daily-s3-policy.json` (replace `BUCKET_NAME`):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:PutObjectAcl",
        "s3:GetObject",
        "s3:GetObjectAcl",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::BUCKET_NAME/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": "arn:aws:s3:::BUCKET_NAME"
    }
  ]
}
```

### Attach Policy to Role

```bash
aws iam put-role-policy \
  --role-name DailyCo \
  --policy-name DailyCoS3Access \
  --policy-document file://daily-s3-policy.json
```

### Get the Role ARN

```bash
aws iam get-role --role-name DailyCo --query 'Role.Arn' --output text
```

Save this ARN - you'll need it in Step 6.

Output looks like: `arn:aws:iam::123456789012:role/DailyCo`

---

## Step 5: Configure Daily.co to Use Your S3

**Official Documentation**: For detailed instructions, see Daily.co's guide on [Storing Recordings in a Custom S3 Bucket](https://docs.daily.co/guides/products/live-streaming-recording/storing-recordings-in-a-custom-s3-bucket)

**Quick Setup:**

1. Go to Daily.co dashboard → **Developers** → **Recording**
2. Select **Amazon S3**
3. Enter:
   - **Bucket Name**: Your bucket name from Step 3
   - **Bucket Region**: `us-east-1` (or your chosen region)
   - **Role ARN**: The ARN from Step 4
4. Click **Save**
5. Daily.co will verify it can access your bucket

---

## Step 6: Configure Reflector

**Location: YOUR SERVER (via SSH)**

Add to `server/.env`:
```bash
ssh user@your-server
cd ~/reflector
nano server/.env
```

Add these lines:
```env
# Daily.co Configuration
DEFAULT_VIDEO_PLATFORM=daily
DAILY_API_KEY=<your-api-key-from-step-2>
DAILY_SUBDOMAIN=<your-subdomain-from-step-1>

# S3 Storage for Daily.co recordings
DAILYCO_STORAGE_AWS_BUCKET_NAME=<your-bucket-from-step-3>
DAILYCO_STORAGE_AWS_REGION=us-east-1
DAILYCO_STORAGE_AWS_ROLE_ARN=<your-role-arn-from-step-4>

# Transcript storage (required for Daily.co multitrack processing)
TRANSCRIPT_STORAGE_BACKEND=local
# Or use S3 for production:
# TRANSCRIPT_STORAGE_BACKEND=aws
# TRANSCRIPT_STORAGE_AWS_ACCESS_KEY_ID=<your-key>
# TRANSCRIPT_STORAGE_AWS_SECRET_ACCESS_KEY=<your-secret>
# TRANSCRIPT_STORAGE_AWS_BUCKET_NAME=reflector-media
# TRANSCRIPT_STORAGE_AWS_REGION=us-east-1
```

---

## Step 7: Restart Services

After changing `.env` files, reload with `up -d`:

```bash
sudo docker compose -f docker-compose.prod.yml up -d server worker
```

**Note**: `docker compose up -d` detects env changes and recreates containers automatically.

---

## Step 8: Test Live Room

1. Visit your Reflector frontend: `https://app.example.com`
2. Go to **Rooms** (or `/rooms`)
3. Click **Create Room** or use test room
4. Click **Join Meeting**
5. Allow camera/microphone access
6. You should see Daily.co video interface
7. Speak for 10-20 seconds
8. Leave the meeting
9. Recording should appear in **Transcripts** within 1-2 minutes

---

## Troubleshooting

### "Failed to create room"

Check `server/.env`:
- `DAILY_API_KEY` is correct
- `DAILY_SUBDOMAIN` matches your Daily.co account
- Restart server after changes

### Recording doesn't appear in S3

1. Check Daily.co dashboard → **Logs** for errors
2. Verify IAM role trust policy has correct Daily.co account ID
3. Test S3 permissions:
   ```bash
   aws s3 ls s3://your-bucket-name
   ```

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

## Webhook Configuration

Reflector automatically configures the Daily.co webhook when the server starts if:
- `DAILY_API_KEY` is set
- `DAILY_SUBDOMAIN` is set
- `BASE_URL` is accessible from the internet

The webhook URL will be: `https://api.example.com/v1/webhooks/daily`

To manually check webhook:
```bash
curl -H "Authorization: Bearer YOUR_DAILY_API_KEY" \
  https://api.daily.co/v1/webhooks
```

---

## Costs

**Daily.co Free Tier:**
- 10,000 participant minutes/month
- Good for ~40 hours of meetings

**AWS S3 Costs:**
- Storage: ~$0.023/GB/month
- 1 hour meeting ≈ 500MB recording
- Example: 10 hours/month ≈ $0.12/month

**Modal.com Processing:**
- Transcription: ~$0.01-0.05 per minute of audio
- Diarization: ~$0.02-0.10 per minute of audio
