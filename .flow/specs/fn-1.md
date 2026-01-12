# PRD: Transcript Chat Assistant (POC)

## Research Complete

**Backend Infrastructure:**
- LLM configured: `reflector/llm.py` using llama-index's `OpenAILike`
- Streaming support: `Settings.llm.astream_chat()` available (configured by LLM class)
- WebSocket infrastructure: Redis pub/sub via `ws_manager`
- Existing pattern: `/v1/transcripts/{transcript_id}/events` WebSocket (broadcast-only)

**Frontend Infrastructure:**
- `useWebSockets` hook pattern established
- Chakra UI v3 with Dialog.Root API
- lucide-react icons available

**Decision: Use existing WebSocket + custom chat UI**

---

## Architecture

```
Frontend                         Backend (FastAPI)
┌──────────────────┐            ┌────────────────────────────┐
│ Transcript Page  │            │ /v1/transcripts/{id}/chat  │
│                  │            │                            │
│ ┌──────────────┐ │            │ WebSocket Endpoint         │
│ │ Chat Dialog  │ │◄──WebSocket│ (bidirectional)            │
│ │              │ │────────────┤ 1. Auth check              │
│ │ - Messages   │ │  send msg  │ 2. Get WebVTT transcript   │
│ │ - Input      │ │            │ 3. Build conversation      │
│ │ - Streaming  │ │◄───────────┤ 4. Call astream_chat()     │
│ └──────────────┘ │  stream    │ 5. Stream tokens via WS    │
│ useTranscriptChat│  response  │                            │
└──────────────────┘            │ ┌────────────────────────┐ │
                                 │ │ LLM (llama-index)      │ │
                                 │ │ Settings.llm          │ │
                                 │ │ astream_chat()        │ │
                                 │ └────────────────────────┘ │
                                 │                            │
                                 │ Existing:                  │
                                 │ - topics_to_webvtt_named() │
                                 └────────────────────────────┘
```

**Note:** This WebSocket is bidirectional (client→server messages) unlike existing broadcast-only pattern (`/events` endpoint).

---

## Components

### Backend

**1. WebSocket Endpoint** (`server/reflector/views/transcripts_chat.py`)

```python
@router.websocket("/transcripts/{transcript_id}/chat")
async def transcript_chat_websocket(
    transcript_id: str,
    websocket: WebSocket,
    user: Optional[auth.UserInfo] = Depends(auth.current_user_optional),
):
    # 1. Auth check
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id_for_http(transcript_id, user_id)

    # 2. Accept WebSocket
    await websocket.accept()

    # 3. Get WebVTT context
    webvtt = topics_to_webvtt_named(
        transcript.topics,
        transcript.participants,
        await _get_is_multitrack(transcript)
    )

    # 4. Configure LLM (sets up Settings.llm with session tracking)
    llm = LLM(settings=settings, temperature=0.7)

    # 5. System message
    system_msg = f"""You are analyzing this meeting transcript (WebVTT):

{webvtt[:15000]}  # Truncate if needed

Answer questions about content, speakers, timeline. Include timestamps when relevant."""

    # 6. Conversation loop
    conversation_history = [{"role": "system", "content": system_msg}]

    try:
        while True:
            # Receive user message
            data = await websocket.receive_json()
            if data["type"] != "message":
                continue

            user_msg = {"role": "user", "content": data["text"]}
            conversation_history.append(user_msg)

            # Stream LLM response
            assistant_msg = ""
            async for chunk in Settings.llm.astream_chat(conversation_history):
                token = chunk.delta
                await websocket.send_json({"type": "token", "text": token})
                assistant_msg += token

            conversation_history.append({"role": "assistant", "content": assistant_msg})
            await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
```

**Message Protocol:**
```typescript
// Client → Server
{type: "message", text: "What was discussed?"}

// Server → Client (streaming)
{type: "token", text: "At "}
{type: "token", text: "01:23"}
...
{type: "done"}
{type: "error", message: "..."} // on errors
```

### Frontend

**2. Chat Hook** (`www/app/(app)/transcripts/useTranscriptChat.ts`)

```typescript
export const useTranscriptChat = (transcriptId: string) => {
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [currentStreamingText, setCurrentStreamingText] = useState("")
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const ws = new WebSocket(`${WEBSOCKET_URL}/v1/transcripts/${transcriptId}/chat`)
    wsRef.current = ws

    ws.onopen = () => console.log("Chat WebSocket connected")

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)

      switch (msg.type) {
        case "token":
          setIsStreaming(true)
          setCurrentStreamingText(prev => prev + msg.text)
          break

        case "done":
          setMessages(prev => [...prev, {
            id: Date.now().toString(),
            role: "assistant",
            text: currentStreamingText,
            timestamp: new Date()
          }])
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
  }, [transcriptId])

  const sendMessage = (text: string) => {
    if (!wsRef.current) return

    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      role: "user",
      text,
      timestamp: new Date()
    }])

    wsRef.current.send(JSON.stringify({type: "message", text}))
  }

  return {messages, sendMessage, isStreaming, currentStreamingText}
}
```

**3. Chat Dialog** (`www/app/(app)/transcripts/TranscriptChatModal.tsx`)

```tsx
import { Dialog, Box, Input, IconButton } from "@chakra-ui/react"
import { MessageCircle } from "lucide-react"

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
  currentStreamingText
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
            {messages.map(msg => (
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
                <Box as="span" className="animate-pulse">▊</Box>
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

// Floating button
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

**4. Integration** (Modify `/transcripts/[transcriptId]/page.tsx`)

```tsx
import { useDisclosure } from "@chakra-ui/react"
import { TranscriptChatModal, TranscriptChatButton } from "../TranscriptChatModal"
import { useTranscriptChat } from "../useTranscriptChat"

export default function TranscriptDetails(details: TranscriptDetails) {
  const params = use(details.params)
  const transcriptId = params.transcriptId

  const { open, onOpen, onClose } = useDisclosure()
  const chat = useTranscriptChat(transcriptId)

  return (
    <>
      {/* Existing transcript UI */}
      <Grid templateColumns="1fr" /* ... */>
        {/* ... existing content ... */}
      </Grid>

      {/* Chat interface */}
      <TranscriptChatModal
        open={open}
        onClose={onClose}
        {...chat}
      />
      <TranscriptChatButton onClick={onOpen} />
    </>
  )
}
```

---

## Data Structures

```typescript
type Message = {
  id: string
  role: "user" | "assistant"
  text: string
  timestamp: Date
}
```

---

## API Specifications

### WebSocket Endpoint

**URL:** `ws://localhost:1250/v1/transcripts/{transcript_id}/chat`

**Auth:** Optional user (same as existing endpoints)

**Client → Server:**
```json
{"type": "message", "text": "What was discussed?"}
```

**Server → Client:**
```json
{"type": "token", "text": "chunk"}
{"type": "done"}
{"type": "error", "message": "error text"}
```

---

## Implementation Notes

**LLM Integration:**
- Instantiate `LLM()` to configure `Settings.llm` with session tracking
- Use `Settings.llm.astream_chat()` directly for streaming
- Chunks have `.delta` property with token text

**WebVTT Context:**
- Reuse `topics_to_webvtt_named()` utility
- Truncate to ~15k chars if needed (known limitation for POC)
- Include in system message

**Conversation State:**
- Store in-memory in WebSocket handler (ephemeral)
- Clear on disconnect
- No persistence (out of scope)

**Error Handling:**
- Basic try/catch with error message to client
- Log errors server-side

---

## File Structure

```
server/reflector/views/
  └── transcripts_chat.py              # New: ~80 lines

www/app/(app)/transcripts/
  ├── [transcriptId]/
  │   └── page.tsx                     # Modified: +10 lines
  ├── useTranscriptChat.ts             # New: ~60 lines
  └── TranscriptChatModal.tsx          # New: ~80 lines
```

**Total:** ~230 lines of code

---

## Dependencies

**Backend:** None (all existing)

**Frontend:** None (Chakra UI + lucide-react already installed)

---

## Out of Scope (POC)

- ❌ Message persistence/history
- ❌ Context window optimization
- ❌ Sentence buffering (token-by-token is fine)
- ❌ Rate limiting beyond auth
- ❌ Tool calling
- ❌ RAG/vector search

**Known Limitations:**
- Long transcripts (>15k chars) will be truncated
- Conversation lost on disconnect
- No error recovery/retry

---

## Acceptance Criteria

- [ ] Floating button on transcript page
- [ ] Click opens dialog with chat interface
- [ ] Send message, receive streaming response
- [ ] LLM has WebVTT transcript context
- [ ] Auth works (optional user)
- [ ] Dialog closes, conversation cleared
- [ ] Works with configured OpenAI-compatible LLM

---

## References

- [LlamaIndex Streaming](https://docs.llamaindex.ai/en/stable/module_guides/deploying/query_engine/streaming/)
- [LlamaIndex OpenAILike](https://docs.llamaindex.ai/en/stable/api_reference/llms/openai_like/)
- [FastAPI WebSocket](https://fastapi.tiangolo.com/advanced/websockets/)
