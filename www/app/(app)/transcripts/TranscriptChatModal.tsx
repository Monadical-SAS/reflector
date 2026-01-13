"use client";

import { useState } from "react";
import { Box, Dialog, Input, IconButton } from "@chakra-ui/react";
import { MessageCircle } from "lucide-react";
import Markdown from "react-markdown";
import "../../styles/markdown.css";
import type { Message } from "./useTranscriptChat";

interface TranscriptChatModalProps {
  open: boolean;
  onClose: () => void;
  messages: Message[];
  sendMessage: (text: string) => void;
  isStreaming: boolean;
  currentStreamingText: string;
}

export function TranscriptChatModal({
  open,
  onClose,
  messages,
  sendMessage,
  isStreaming,
  currentStreamingText,
}: TranscriptChatModalProps) {
  const [input, setInput] = useState("");

  const handleSend = () => {
    if (!input.trim()) return;
    sendMessage(input);
    setInput("");
  };

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
                {msg.role === "user" ? (
                  msg.text
                ) : (
                  <div className="markdown">
                    <Markdown>{msg.text}</Markdown>
                  </div>
                )}
              </Box>
            ))}

            {isStreaming && (
              <Box p={3} bg="gray.50" borderRadius="md">
                <div className="markdown">
                  <Markdown>{currentStreamingText}</Markdown>
                </div>
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
  );
}

export function TranscriptChatButton({ onClick }: { onClick: () => void }) {
  return (
    <IconButton
      position="fixed"
      bottom="24px"
      right="24px"
      onClick={onClick}
      size="lg"
      colorPalette="blue"
      borderRadius="full"
      aria-label="Open chat"
    >
      <MessageCircle />
    </IconButton>
  );
}
