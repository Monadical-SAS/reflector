"use client";

import { useEffect, useState, useRef } from "react";
import { getSession } from "next-auth/react";
import { WEBSOCKET_URL } from "../../lib/apiClient";
import { assertExtendedToken } from "../../lib/types";

export type Message = {
  id: string;
  role: "user" | "assistant";
  text: string;
  timestamp: Date;
};

export type UseTranscriptChat = {
  messages: Message[];
  sendMessage: (text: string) => void;
  isStreaming: boolean;
  currentStreamingText: string;
};

export const useTranscriptChat = (transcriptId: string): UseTranscriptChat => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStreamingText, setCurrentStreamingText] = useState("");
  const wsRef = useRef<WebSocket | null>(null);
  const streamingTextRef = useRef<string>("");
  const isMountedRef = useRef<boolean>(true);

  useEffect(() => {
    isMountedRef.current = true;

    const connectWebSocket = async () => {
      const url = `${WEBSOCKET_URL}/v1/transcripts/${transcriptId}/chat`;

      // Get auth token for WebSocket subprotocol
      let protocols: string[] | undefined;
      try {
        const session = await getSession();
        if (session) {
          const token = assertExtendedToken(session).accessToken;
          // Pass token via subprotocol: ["bearer", token]
          protocols = ["bearer", token];
        }
      } catch (error) {
        console.warn("Failed to get auth token for WebSocket:", error);
      }

      const ws = new WebSocket(url, protocols);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("Chat WebSocket connected");
      };

      ws.onmessage = (event) => {
        if (!isMountedRef.current) return;

        const msg = JSON.parse(event.data);

        switch (msg.type) {
          case "token":
            setIsStreaming(true);
            streamingTextRef.current += msg.text;
            setCurrentStreamingText(streamingTextRef.current);
            break;

          case "done":
            // CRITICAL: Save the text BEFORE resetting the ref
            // The setMessages callback may execute later, after ref is reset
            const finalText = streamingTextRef.current;

            setMessages((prev) => [
              ...prev,
              {
                id: Date.now().toString(),
                role: "assistant",
                text: finalText,
                timestamp: new Date(),
              },
            ]);
            streamingTextRef.current = "";
            setCurrentStreamingText("");
            setIsStreaming(false);
            break;

          case "error":
            console.error("Chat error:", msg.message);
            setIsStreaming(false);
            break;
        }
      };

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
      };

      ws.onclose = () => {
        console.log("Chat WebSocket closed");
      };
    };

    connectWebSocket();

    return () => {
      isMountedRef.current = false;
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [transcriptId]);

  const sendMessage = (text: string) => {
    if (!wsRef.current) return;

    setMessages((prev) => [
      ...prev,
      {
        id: Date.now().toString(),
        role: "user",
        text,
        timestamp: new Date(),
      },
    ]);

    wsRef.current.send(JSON.stringify({ type: "message", text }));
  };

  return { messages, sendMessage, isStreaming, currentStreamingText };
};
