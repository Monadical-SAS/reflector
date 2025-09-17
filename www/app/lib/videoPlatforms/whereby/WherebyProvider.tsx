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

// Whereby embed element type declaration
declare global {
  namespace JSX {
    interface IntrinsicElements {
      "whereby-embed": React.DetailedHTMLProps<
        React.HTMLAttributes<HTMLElement> & {
          room?: string;
          style?: React.CSSProperties;
        },
        HTMLElement
      >;
    }
  }
}

const WherebyProvider = forwardRef<HTMLElement, VideoPlatformComponentProps>(
  ({ meeting, roomRef, onReady, onConsentGiven, onConsentDeclined }, ref) => {
    const [wherebyLoaded, setWherebyLoaded] = useState(false);
    const internalRef = useRef<HTMLElement>(null);
    const elementRef = roomRef || internalRef;

    // Expose the element ref through the forwarded ref
    useImperativeHandle(ref, () => elementRef.current!, [elementRef]);

    // Load Whereby SDK
    useEffect(() => {
      if (typeof window !== "undefined") {
        import("@whereby.com/browser-sdk/embed")
          .then(() => {
            setWherebyLoaded(true);
          })
          .catch(console.error);
      }
    }, []);

    // Handle leave event
    const handleLeave = useCallback(() => {
      // This will be handled by the parent component
      // through router navigation or other means
    }, []);

    // Handle ready event
    const handleReady = useCallback(() => {
      if (onReady) {
        onReady();
      }
    }, [onReady]);

    // Set up event listeners
    useEffect(() => {
      if (!wherebyLoaded || !elementRef.current) return;

      const element = elementRef.current;

      element.addEventListener("leave", handleLeave);
      element.addEventListener("ready", handleReady);

      return () => {
        element.removeEventListener("leave", handleLeave);
        element.removeEventListener("ready", handleReady);
      };
    }, [wherebyLoaded, handleLeave, handleReady, elementRef]);

    if (!wherebyLoaded || !meeting) {
      return null;
    }

    const roomUrl = meeting.host_room_url || meeting.room_url;

    return (
      <whereby-embed
        ref={elementRef}
        room={roomUrl}
        style={{ width: "100vw", height: "100vh" }}
      />
    );
  },
);

WherebyProvider.displayName = "WherebyProvider";

export default WherebyProvider;
