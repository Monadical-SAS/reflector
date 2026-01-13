# fn-1.7 Integrate into transcript page

## Description
Add TranscriptChatModal and TranscriptChatButton to the transcript details page. Use `useDisclosure` hook for modal state, instantiate `useTranscriptChat` hook with transcriptId, and render both components.

## Acceptance
- [ ] Import useDisclosure from @chakra-ui/react
- [ ] Import TranscriptChatModal and TranscriptChatButton components
- [ ] Import useTranscriptChat hook
- [ ] Add useDisclosure hook for modal open/close state
- [ ] Add useTranscriptChat hook with transcriptId
- [ ] Render TranscriptChatModal with all required props
- [ ] Render TranscriptChatButton with onClick handler
- [ ] Floating button appears on transcript page
- [ ] Click button opens chat dialog
- [ ] Dialog integrates with existing page layout

## Done summary
- Added TranscriptChatModal and TranscriptChatButton to transcript details page
- Imported useDisclosure hook from @chakra-ui/react for modal state management
- Integrated useTranscriptChat hook with transcriptId for WebSocket connection
- Rendered floating chat button in bottom-right corner and modal dialog
- Chat interface now accessible from all completed transcript pages

Verification:
- Code formatting passed (pnpm format)
- Pre-commit hooks passed
- Integration follows existing patterns from PRD spec
## Evidence
- Commits: e7dc003a1dacdbc1992265e6c5b0f0cf522f8530
- Tests: pnpm format
- PRs: