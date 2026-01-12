# Task 5: Frontend WebSocket Hook

**File:** `www/app/(app)/transcripts/useTranscriptChat.ts`
**Lines:** ~60
**Dependencies:** Task 1 (protocol defined)

## Objective
Create React hook for WebSocket chat communication.

## Implementation
```typescript
import { useEffect, useState, useRef } from "react"
import { WEBSOCKET_URL } from "../../lib/apiClient"

type Message = {
  id: string
  role: "user" | "assistant"
  text: string
  timestamp: Date
}

export const useTranscriptChat = (transcriptId: string) => {
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [currentStreamingText, setCurrentStreamingText] = useState("")
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const ws = new WebSocket(
      `${WEBSOCKET_URL}/v1/transcripts/${transcriptId}/chat`
    )
    wsRef.current = ws

    ws.onopen = () => console.log("Chat WebSocket connected")

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)

      switch (msg.type) {
        case "token":
          setIsStreaming(true)
          setCurrentStreamingText((prev) => prev + msg.text)
          break

        case "done":
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now().toString(),
              role: "assistant",
              text: currentStreamingText,
              timestamp: new Date(),
            },
          ])
          setCurrentStreamingText("")
          setIsStreaming(false)
          break

        case "error":
          console.error("Chat error:", msg.message)
          setIsStreaming(false)
          break
      }
    }

    ws.onerror = (error) => console.error("WebSocket error:", error)
    ws.onclose = () => console.log("Chat WebSocket closed")

    return () => ws.close()
  }, [transcriptId, currentStreamingText])

  const sendMessage = (text: string) => {
    if (!wsRef.current) return

    setMessages((prev) => [
      ...prev,
      {
        id: Date.now().toString(),
        role: "user",
        text,
        timestamp: new Date(),
      },
    ])

    wsRef.current.send(JSON.stringify({ type: "message", text }))
  }

  return { messages, sendMessage, isStreaming, currentStreamingText }
}
```

## Validation
- [ ] Hook connects to WebSocket
- [ ] Sends messages to server
- [ ] Receives streaming tokens
- [ ] Accumulates tokens into messages
- [ ] Handles done/error events
- [ ] Closes connection on unmount

## Notes
- Test with browser console first
- Verify message format matches backend protocol
