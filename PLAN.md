# Daily.co Migration Plan - Feature Parity Approach

## Overview

This plan outlines a systematic migration from Whereby to Daily.co, focusing on **1:1 feature parity** without introducing new capabilities. The goal is to improve code quality, developer experience, and platform reliability while maintaining the exact same user experience and processing pipeline.

## Migration Principles

1. **No Breaking Changes**: Existing recordings and workflows must continue to work
2. **Feature Parity First**: Match current functionality exactly before adding improvements
3. **Gradual Rollout**: Use feature flags to control migration per room/user
4. **Minimal Risk**: Keep changes isolated and reversible

## Phase 1: Foundation

### 1.1 Environment Setup
**Owner**: Backend Developer

- [ ] Create Daily.co account and obtain API credentials (PENDING - User to provide)
- [x] Add environment variables to `.env` files:
  ```bash
  DAILY_API_KEY=your-api-key
  DAILY_WEBHOOK_SECRET=your-webhook-secret
  DAILY_SUBDOMAIN=your-subdomain
  AWS_DAILY_ROLE_ARN=arn:aws:iam::xxx:role/daily-recording
  ```
- [ ] Set up Daily.co webhook endpoint in dashboard (PENDING - Credentials needed)
- [ ] Configure S3 bucket permissions for Daily.co (PENDING - Credentials needed)

### 1.2 Database Migration
**Owner**: Backend Developer

- [x] Create Alembic migration:
  ```python
  # server/migrations/versions/20250801180012_add_platform_support.py
  def upgrade():
      op.add_column('rooms', sa.Column('platform', sa.String(), server_default='whereby'))
      op.add_column('meetings', sa.Column('platform', sa.String(), server_default='whereby'))
  ```
- [ ] Run migration on development database (USER TO RUN: `uv run alembic upgrade head`)
- [x] Update models to include platform field

### 1.3 Feature Flag System
**Owner**: Full-stack Developer

- [x] Implement feature flag in backend settings:
  ```python
  DAILY_MIGRATION_ENABLED = env.bool("DAILY_MIGRATION_ENABLED", False)
  DAILY_MIGRATION_ROOM_IDS = env.list("DAILY_MIGRATION_ROOM_IDS", [])
  ```
- [x] Add platform selection logic to room creation
- [ ] Create admin UI to toggle platform per room (FUTURE - Not in Phase 1)

### 1.4 Daily.co API Client
**Owner**: Backend Developer

- [x] Create `server/reflector/video_platforms/` with core functionality:
  - `create_meeting()` - Match Whereby's meeting creation
  - `get_room_sessions()` - Room status checking
  - `delete_room()` - Cleanup functionality
- [x] Add comprehensive error handling
- [ ] Write unit tests for API client (Phase 4)

## Phase 2: Backend Integration

### 2.1 Webhook Handler
**Owner**: Backend Developer

- [x] Create `server/reflector/views/daily.py` webhook endpoint
- [x] Implement HMAC signature verification
- [x] Handle events:
  - `participant.joined`
  - `participant.left`
  - `recording.started`
  - `recording.ready-to-download`
- [x] Map Daily.co events to existing database updates
- [x] Register webhook router in main app
- [ ] Add webhook tests with mocked events (Phase 4)

### 2.2 Room Management Updates
**Owner**: Backend Developer

- [x] Update `server/reflector/views/rooms.py`:
  ```python
  # Uses platform abstraction layer
  platform = get_platform_for_room(room.id)
  client = create_platform_client(platform)
  meeting_data = await client.create_meeting(...)
  ```
- [x] Ensure room URLs are stored correctly
- [x] Update meeting status checks to support both platforms
- [ ] Test room creation/deletion for both platforms (Phase 4)

## Phase 3: Frontend Migration

### 3.1 Daily.co React Setup
**Owner**: Frontend Developer

- [x] Install Daily.co packages:
  ```bash
  yarn add @daily-co/daily-react @daily-co/daily-js
  ```
- [x] Create platform-agnostic components structure
- [x] Set up TypeScript interfaces for meeting data

### 3.2 Room Component Refactor
**Owner**: Frontend Developer

- [x] Create platform-agnostic room component:
  ```tsx
  // www/app/[roomName]/components/RoomContainer.tsx
  export default function RoomContainer({ params }) {
    const platform = meeting.response.platform || "whereby";
    if (platform === 'daily') {
      return <DailyRoom meeting={meeting.response} />
    }
    return <WherebyRoom meeting={meeting.response} />
  }
  ```
- [x] Implement `DailyRoom` component with:
  - Call initialization using DailyIframe
  - Recording consent flow
  - Leave meeting handling
- [x] Extract `WherebyRoom` component maintaining existing functionality
- [x] Simplified focus management (Daily.co handles this internally)

### 3.3 Consent Dialog Integration
**Owner**: Frontend Developer

- [x] Adapt consent dialog for Daily.co (uses same API endpoints)
- [x] Ensure recording status is properly tracked
- [x] Maintain consistent consent UI across both platforms
- [ ] Test consent flow with Daily.co recordings (Phase 4)

## Phase 4: Testing & Validation

### 4.1 Integration Testing
**Owner**: QA + Development Team

- [ ] Test complete flow for both platforms:
  - Room creation
  - Join meeting
  - Recording consent
  - Recording to S3
  - Webhook processing
  - Transcript generation
- [ ] Verify S3 paths are compatible
- [ ] Check recording format (MP4) matches
- [ ] Ensure processing pipeline works unchanged

### 4.2 Performance Testing
**Owner**: Backend Developer

- [ ] Compare API response times
- [ ] Measure webhook latency
- [ ] Test with multiple concurrent rooms
- [ ] Verify participant count accuracy

### 4.3 User Acceptance Testing
**Owner**: Product Team

- [ ] Create test rooms with Daily.co
- [ ] Have team members test call quality
- [ ] Verify UI/UX matches expectations
- [ ] Document any visual differences

## Phase 5: Gradual Rollout

### 5.1 Internal Testing
**Owner**: Development Team

- [ ] Enable Daily.co for internal test rooms
- [ ] Monitor logs and error rates
- [ ] Fix any issues discovered
- [ ] Verify recordings process correctly

### 5.2 Beta Rollout
**Owner**: DevOps + Product

- [ ] Select beta users/rooms
- [ ] Enable Daily.co via feature flag
- [ ] Monitor metrics:
  - Error rates
  - Recording success
  - User feedback
- [ ] Create rollback plan

### 5.3 Full Migration
**Owner**: DevOps + Product

- [ ] Gradually increase Daily.co usage
- [ ] Monitor all metrics
- [ ] Plan Whereby sunset timeline
- [ ] Update documentation

## Success Criteria

### Technical Metrics
- [ ] API error rate < 0.1%
- [ ] Webhook delivery rate > 99.9%
- [ ] Recording success rate matches Whereby
- [ ] No increase in processing failures

### User Experience
- [ ] No user-reported regressions
- [ ] Call quality ratings maintained
- [ ] Recording consent flow works smoothly
- [ ] Participant tracking is accurate

### Code Quality
- [ ] Removed 70+ lines of focus management code
- [ ] Improved TypeScript coverage
- [ ] Better error handling
- [ ] Cleaner React component structure

## Rollback Plan

If issues arise during migration:

1. **Immediate**: Disable Daily.co feature flag
2. **Short-term**: Revert frontend components via git
3. **Database**: Platform field defaults to 'whereby'
4. **Full rollback**: Remove Daily.co code (isolated in separate files)

## Post-Migration Opportunities

Once feature parity is achieved and stable:

1. **Raw-tracks recording** for better diarization
2. **Real-time transcription** via Daily.co API
3. **Advanced analytics** and participant insights
4. **Custom UI** improvements
5. **Performance optimizations**

## Phase Dependencies

- Backend Integration requires Foundation to be complete
- Frontend Migration can start after Backend API client is ready
- Testing requires both Backend and Frontend to be complete
- Rollout begins after successful testing

## Risk Matrix

| Risk | Probability | Impact | Mitigation |
|------|-------------|---------|------------|
| API differences | Low | Medium | Abstraction layer |
| Recording format issues | Low | High | Extensive testing |
| User confusion | Low | Low | Gradual rollout |
| Performance degradation | Low | Medium | Monitoring |

## Communication Plan

1. **Week 1**: Announce migration plan to team
2. **Week 2**: Update on development progress
3. **Beta Launch**: Email to beta users
4. **Full Launch**: User notification (if UI changes)
5. **Post-Launch**: Success metrics report

---

This plan prioritizes stability and risk mitigation through a phased approach. The modular implementation allows for adjustments based on findings during development.
