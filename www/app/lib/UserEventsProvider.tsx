"use client";

import React, { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { $api, WEBSOCKET_URL } from "./apiClient";
import { useAuth } from "./AuthProvider";

type UserEvent = {
  event: string;
  data: any;
};

class UserEventsStore {
  private socket: WebSocket | null = null;
  private listeners: Set<(event: MessageEvent) => void> = new Set();
  private refCount = 0;
  private closeTimeoutId: number | null = null;
  private isConnecting = false;

  ensureConnection(url: string) {
    if (typeof window === "undefined") return;
    if (this.closeTimeoutId !== null) {
      clearTimeout(this.closeTimeoutId);
      this.closeTimeoutId = null;
    }
    if (this.isConnecting) return;
    if (
      this.socket &&
      (this.socket.readyState === WebSocket.OPEN ||
        this.socket.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }
    this.isConnecting = true;
    const ws = new WebSocket(url);
    this.socket = ws;
    ws.onmessage = (event: MessageEvent) => {
      this.listeners.forEach((listener) => {
        try {
          listener(event);
        } catch {}
      });
    };
    ws.onopen = () => {
      if (this.socket === ws) this.isConnecting = false;
    };
    ws.onclose = () => {
      if (this.socket === ws) {
        this.socket = null;
        this.isConnecting = false;
      }
    };
    ws.onerror = () => {
      if (this.socket === ws) this.isConnecting = false;
    };
  }

  subscribe(listener: (event: MessageEvent) => void): () => void {
    this.listeners.add(listener);
    this.refCount += 1;
    if (this.closeTimeoutId !== null) {
      clearTimeout(this.closeTimeoutId);
      this.closeTimeoutId = null;
    }
    return () => {
      this.listeners.delete(listener);
      this.refCount = Math.max(0, this.refCount - 1);
      if (this.refCount === 0) {
        this.closeTimeoutId = window.setTimeout(() => {
          try {
            this.socket?.close();
          } catch {}
          this.socket = null;
          this.closeTimeoutId = null;
        }, 1000);
      }
    };
  }
}

const sharedStore = new UserEventsStore();

export function UserEventsProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const auth = useAuth();
  const queryClient = useQueryClient();
  const tokenRef = useRef<string | null>(null);
  const detachRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (auth.status !== "authenticated") {
      if (detachRef.current) {
        try {
          detachRef.current();
        } catch {}
        detachRef.current = null;
      }
      tokenRef.current = null;
      return;
    }

    if (!tokenRef.current && (auth as any).accessToken) {
      tokenRef.current = (auth as any).accessToken as string;
    }
    const pinnedToken = tokenRef.current;
    const url = `${WEBSOCKET_URL}/v1/events${
      pinnedToken ? `?token=${encodeURIComponent(pinnedToken)}` : ""
    }`;

    sharedStore.ensureConnection(url);

    const onMessage = (event: MessageEvent) => {
      try {
        const msg: UserEvent = JSON.parse(event.data);
        const eventName = msg.event;
        const transcriptId = (msg.data as any).id as string;

        const invalidateList = () =>
          queryClient.invalidateQueries({
            predicate: (query) => {
              const key = query.queryKey;
              return key.some(
                (k) =>
                  typeof k === "string" && k.includes("/v1/transcripts/search"),
              );
            },
          });

        switch (eventName) {
          case "TRANSCRIPT_CREATED":
          case "TRANSCRIPT_DELETED":
          case "TRANSCRIPT_STATUS":
          case "FINAL_TITLE":
          case "DURATION":
            invalidateList();
            break;

          default:
            // Ignore other content events for list updates
            break;
        }
      } catch {}
    };

    const unsubscribe = sharedStore.subscribe(onMessage);
    detachRef.current = unsubscribe;
    return () => {
      if (detachRef.current) {
        detachRef.current();
        detachRef.current = null;
      }
    };
  }, [auth.status, queryClient]);

  return <>{children}</>;
}
