# fn-1.5 Frontend WebSocket hook

## Description
Implement React hook `useTranscriptChat` for bidirectional WebSocket chat with transcript assistant.

## Acceptance
- [x] Hook exported from `www/app/(app)/transcripts/useTranscriptChat.ts`
- [x] Connects to `/v1/transcripts/{transcriptId}/chat` WebSocket endpoint
- [x] Manages messages array with user and assistant messages
- [x] Handles streaming tokens (`type: "token"`) with proper accumulation
- [x] Handles completion (`type: "done"`) by adding message to history
- [x] Handles errors (`type: "error"`) with console logging
- [x] Provides `sendMessage(text)` function for user input
- [x] Returns `{messages, sendMessage, isStreaming, currentStreamingText}`
- [x] Proper TypeScript types (Message, UseTranscriptChat)
- [x] Memory leak prevention (isMounted check, proper cleanup)
- [x] WebSocket cleanup on unmount

## Done summary
Implemented useTranscriptChat React hook with WebSocket streaming, message management, and TypeScript types.

The hook provides:
- Bidirectional WebSocket connection to `/v1/transcripts/{transcriptId}/chat`
- Token streaming with ref-based accumulation (prevents stale closures)
- Conversation history management (user + assistant messages)
- Proper mounted state tracking to prevent memory leaks
- TypeScript type safety with Message and UseTranscriptChat interfaces
- WebSocket lifecycle management (connect, cleanup on unmount)

Production-ready improvements over spec:
- `streamingTextRef` instead of state-based accumulation (avoids closure bugs)
- `isMountedRef` for preventing setState on unmounted component
- Proper TypeScript typing for all exports
## Evidence
- Commits:
- Tests:
- PRs: