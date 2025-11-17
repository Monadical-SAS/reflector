# Daily.co REST API Documentation

This directory contains AI-readable markdown versions of the **complete** Daily.co REST API documentation.

**IMPORTANT:** This is a standalone documentation directory. The crawler script does NOT depend on project dependencies.

## Contents

- **rest-api/** - Complete Daily.co REST API reference
- **crawl_dailyco_docs.py** - Standalone dynamic crawler script

## Documentation Coverage

The script automatically fetches ALL REST API pages from the sitemap:

- **Rooms** - Create, configure, manage rooms
- **Meetings** - Get meeting info and participants
- **Recordings** - Cloud and raw-tracks recording management
- **Webhooks** - All webhook events and management
  - Including all event types: recording, transcript, streaming, dialin/out, participants
- **Meeting Tokens** - Authentication and access control
- **Batch Processor** - Async job management
- **Transcription** - Live and batch transcription
- **Phone/Dialin** - SIP and phone integration
- **Live Streaming** - RTMP streaming configuration
- **Logs** - API and meeting logs
- **Domain Config** - Domain-level settings

## Documentation Structure

All pages organized by URL path:
- `rest-api/rooms/` - Room management endpoints
- `rest-api/webhooks/events/` - Individual webhook event schemas
- `rest-api/recordings/` - Recording management
- etc.

Each markdown file includes:
- Source URL at the top for reference
- Main content only (navigation/headers/footers stripped)
- Preserved links and formatting

## Usage

These docs are intended for AI assistants to quickly reference Daily.co REST API capabilities when working with the Reflector codebase.

## Updating Documentation

The crawler dynamically fetches the sitemap and crawls ALL pages automatically:

```bash
# Install crawler dependencies (only needed once)
pip install requests beautifulsoup4 html2text lxml

# Run the crawler from the server directory
cd server
python docs/dailyco/crawl_dailyco_docs.py
```

The script will:
1. Fetch the complete sitemap from docs.daily.co
2. Extract all REST API URLs
3. Crawl each page and strip navigation/headers
4. Save as clean markdown

## Source

All documentation dynamically crawled from: https://docs.daily.co/sitemap.xml

**Parsed at:** 2025-11-17 20:53:08 UTC
