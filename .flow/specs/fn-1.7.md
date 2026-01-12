# Task 7: Integrate into Transcript Page

**File:** `www/app/(app)/transcripts/[transcriptId]/page.tsx` (modify)
**Lines:** ~15
**Dependencies:** Task 5, Task 6

## Objective
Add chat components to transcript detail page.

## Implementation
```typescript
// Add imports
import { useDisclosure } from "@chakra-ui/react"
import {
  TranscriptChatModal,
  TranscriptChatButton,
} from "../TranscriptChatModal"
import { useTranscriptChat } from "../useTranscriptChat"

// Inside component:
export default function TranscriptDetails(details: TranscriptDetails) {
  const params = use(details.params)
  const transcriptId = params.transcriptId

  // Add chat state
  const { open, onOpen, onClose } = useDisclosure()
  const chat = useTranscriptChat(transcriptId)

  return (
    <>
      {/* Existing Grid with transcript content */}
      <Grid templateColumns="1fr" templateRows="auto minmax(0, 1fr)" /* ... */>
        {/* ... existing content ... */}
      </Grid>

      {/* Chat interface */}
      <TranscriptChatModal open={open} onClose={onClose} {...chat} />
      <TranscriptChatButton onClick={onOpen} />
    </>
  )
}
```

## Validation
- [ ] Button appears on transcript page
- [ ] Clicking button opens dialog
- [ ] Chat works end-to-end
- [ ] Dialog closes properly
- [ ] No layout conflicts with existing UI
- [ ] Button doesn't overlap other elements

## Notes
- Test on different transcript pages
- Verify z-index for button and dialog
