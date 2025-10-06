"use client";

import React, { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { WEBSOCKET_URL } from "./apiClient";
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

  ensureConnection(url: string, subprotocols?: string[]) {
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
    const ws = new WebSocket(url, subprotocols || []);
    this.socket = ws;
    ws.onmessage = (event: MessageEvent) => {
      this.listeners.forEach((listener) => {
        try {
          listener(event);
        } catch (err) {
          console.error("UserEvents listener error", err);
        }
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
          if (this.socket) {
            try {
              this.socket.close();
            } catch (err) {
              console.warn("Error closing user events socket", err);
            }
          }
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
    // Only tear down when the user is truly unauthenticated
    if (auth.status === "unauthenticated") {
      if (detachRef.current) {
        try {
          detachRef.current();
        } catch (err) {
          console.warn("Error detaching UserEvents listener", err);
        }
        detachRef.current = null;
      }
      tokenRef.current = null;
      return;
    }

    // During loading/refreshing, keep the existing connection intact
    if (auth.status !== "authenticated") {
      return;
    }

    // Authenticated: pin the initial token for the lifetime of this WS connection
    if (!tokenRef.current && (auth as any).accessToken) {
      tokenRef.current = (auth as any).accessToken as string;
    }
    const pinnedToken = tokenRef.current;
    const url = `${WEBSOCKET_URL}/v1/events`;

    // Ensure a single shared connection
    sharedStore.ensureConnection(
      url,
      pinnedToken ? ["bearer", pinnedToken] : undefined,
    );

    // Subscribe once; avoid re-subscribing during transient status changes
    if (!detachRef.current) {
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
                    typeof k === "string" &&
                    k.includes("/v1/transcripts/search"),
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
        } catch (err) {
          console.warn("Invalid user event message", event.data);
        }
      };

      const unsubscribe = sharedStore.subscribe(onMessage);
      detachRef.current = unsubscribe;
    }
  }, [auth.status, queryClient]);

  // On unmount, detach the listener and clear the pinned token
  useEffect(() => {
    return () => {
      if (detachRef.current) {
        try {
          detachRef.current();
        } catch (err) {
          console.warn("Error detaching UserEvents listener on unmount", err);
        }
        detachRef.current = null;
      }
      tokenRef.current = null;
    };
  }, []);

  return <>{children}</>;
}
