# Task 6: Chat Dialog Component

**File:** `www/app/(app)/transcripts/TranscriptChatModal.tsx`
**Lines:** ~90
**Dependencies:** Task 5 (hook interface)

## Objective
Create Chakra UI v3 Dialog component for chat interface.

## Implementation
```typescript
"use client"

import { useState } from "react"
import { Dialog, Box, Input, IconButton } from "@chakra-ui/react"
import { MessageCircle } from "lucide-react"

type Message = {
  id: string
  role: "user" | "assistant"
  text: string
  timestamp: Date
}

interface TranscriptChatModalProps {
  open: boolean
  onClose: () => void
  messages: Message[]
  sendMessage: (text: string) => void
  isStreaming: boolean
  currentStreamingText: string
}

export function TranscriptChatModal({
  open,
  onClose,
  messages,
  sendMessage,
  isStreaming,
  currentStreamingText,
}: TranscriptChatModalProps) {
  const [input, setInput] = useState("")

  const handleSend = () => {
    if (!input.trim()) return
    sendMessage(input)
    setInput("")
  }

  return (
    <Dialog.Root open={open} onOpenChange={(e) => !e.open && onClose()}>
      <Dialog.Backdrop />
      <Dialog.Positioner>
        <Dialog.Content maxW="500px" h="600px">
          <Dialog.Header>Transcript Chat</Dialog.Header>

          <Dialog.Body overflowY="auto">
            {messages.map((msg) => (
              <Box
                key={msg.id}
                p={3}
                mb={2}
                bg={msg.role === "user" ? "blue.50" : "gray.50"}
                borderRadius="md"
              >
                {msg.text}
              </Box>
            ))}

            {isStreaming && (
              <Box p={3} bg="gray.50" borderRadius="md">
                {currentStreamingText}
                <Box as="span" className="animate-pulse">
                  ▊
                </Box>
              </Box>
            )}
          </Dialog.Body>

          <Dialog.Footer>
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="Ask about transcript..."
              disabled={isStreaming}
            />
          </Dialog.Footer>
        </Dialog.Content>
      </Dialog.Positioner>
    </Dialog.Root>
  )
}

export function TranscriptChatButton({ onClick }: { onClick: () => void }) {
  return (
    <IconButton
      position="fixed"
      bottom="24px"
      right="24px"
      onClick={onClick}
      size="lg"
      colorScheme="blue"
      borderRadius="full"
      aria-label="Open chat"
    >
      <MessageCircle />
    </IconButton>
  )
}
```

## Validation
- [ ] Dialog opens/closes correctly
- [ ] Messages display (user: blue, assistant: gray)
- [ ] Streaming text shows with cursor
- [ ] Input disabled during streaming
- [ ] Enter key sends message
- [ ] Dialog scrolls with content
- [ ] Floating button positioned correctly

## Notes
- Test with mock data before connecting hook
- Verify Chakra v3 Dialog.Root API
