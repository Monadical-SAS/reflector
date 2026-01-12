# Task 8: End-to-End Testing

**File:** N/A (testing)
**Lines:** 0
**Dependencies:** All tasks (1-7)

## Objective
Validate complete feature functionality.

## Test Scenarios

### 1. Basic Flow
- [ ] Navigate to transcript page
- [ ] Click floating button
- [ ] Dialog opens with "Transcript Chat" header
- [ ] Type "What was discussed?"
- [ ] Press Enter
- [ ] Streaming response appears token-by-token
- [ ] Response completes with relevant content
- [ ] Ask follow-up question
- [ ] Conversation context maintained

### 2. Edge Cases
- [ ] Empty message (doesn't send)
- [ ] Very long transcript (>15k chars truncated)
- [ ] Network disconnect (graceful error)
- [ ] Multiple rapid messages (queued correctly)
- [ ] Close dialog mid-stream (conversation cleared)
- [ ] Reopen dialog (fresh conversation)

### 3. Auth
- [ ] Works with logged-in user
- [ ] Works with anonymous user
- [ ] Private transcript blocked for wrong user

### 4. UI/UX
- [ ] Button doesn't cover other UI elements
- [ ] Dialog scrolls properly
- [ ] Streaming cursor visible
- [ ] Input disabled during streaming
- [ ] Messages clearly distinguished (user vs assistant)

## Bugs to Watch
- WebSocket connection leaks (check browser devtools)
- Streaming text accumulation bugs
- Race conditions on rapid messages
- Memory leaks from conversation history
