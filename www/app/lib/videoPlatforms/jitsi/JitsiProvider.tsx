"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  forwardRef,
  useImperativeHandle,
} from "react";
import { VideoPlatformComponentProps } from "../types";

const JitsiProvider = forwardRef<HTMLElement, VideoPlatformComponentProps>(
  ({ meeting, roomRef, onReady, onConsentGiven, onConsentDeclined }, ref) => {
    const [jitsiReady, setJitsiReady] = useState(false);
    const internalRef = useRef<HTMLIFrameElement>(null);
    const iframeRef =
      (roomRef as React.RefObject<HTMLIFrameElement>) || internalRef;

    // Expose the element ref through the forwarded ref
    useImperativeHandle(ref, () => iframeRef.current!, [iframeRef]);

    // Handle iframe load
    const handleLoad = useCallback(() => {
      setJitsiReady(true);
      if (onReady) {
        onReady();
      }
    }, [onReady]);

    // Set up event listeners
    useEffect(() => {
      if (!iframeRef.current) return;

      const iframe = iframeRef.current;
      iframe.addEventListener("load", handleLoad);

      return () => {
        iframe.removeEventListener("load", handleLoad);
      };
    }, [handleLoad]);

    if (!meeting) {
      return null;
    }

    // For Jitsi, we use the room_url (user JWT) or host_room_url (moderator JWT)
    const roomUrl = meeting.host_room_url || meeting.room_url;

    return (
      <iframe
        ref={iframeRef}
        src={roomUrl}
        style={{
          width: "100vw",
          height: "100vh",
          border: "none",
        }}
        allow="camera; microphone; fullscreen; display-capture; autoplay"
        title="Jitsi Meet"
      />
    );
  },
);

JitsiProvider.displayName = "JitsiProvider";

export default JitsiProvider;
