"use client";

import React, { createContext, useContext, useEffect, useState } from "react";

// Map of meetingId -> accepted (true/false)
type ConsentMap = Map<string, boolean>;

type ConsentContextState =
  | { ready: false }
  | {
      ready: true;
      consentForMeetings: ConsentMap;
    };

interface RecordingConsentContextValue {
  state: ConsentContextState;
  touch: (meetingId: string, accepted: boolean) => void;
  hasAnswered: (meetingId: string) => boolean;
  hasAccepted: (meetingId: string) => boolean;
}

const RecordingConsentContext = createContext<
  RecordingConsentContextValue | undefined
>(undefined);

export const useRecordingConsent = () => {
  const context = useContext(RecordingConsentContext);
  if (!context) {
    throw new Error(
      "useRecordingConsent must be used within RecordingConsentProvider",
    );
  }
  return context;
};

interface RecordingConsentProviderProps {
  children: React.ReactNode;
}

const LOCAL_STORAGE_KEY = "recording_consent_meetings";

// Format: "meetingId|T" or "meetingId|F", legacy format "meetingId" is treated as accepted
const encodeEntry = (meetingId: string, accepted: boolean): string =>
  `${meetingId}|${accepted ? "T" : "F"}`;

const decodeEntry = (
  entry: string,
): { meetingId: string; accepted: boolean } | null => {
  if (!entry || typeof entry !== "string") return null;
  const pipeIndex = entry.lastIndexOf("|");
  if (pipeIndex === -1) {
    // Legacy format: no pipe means accepted (backward compat)
    return { meetingId: entry, accepted: true };
  }
  const suffix = entry.slice(pipeIndex + 1);
  const meetingId = entry.slice(0, pipeIndex);
  if (!meetingId) return null;
  // T = accepted, F = rejected, anything else = accepted (safe default)
  const accepted = suffix !== "F";
  return { meetingId, accepted };
};

export const RecordingConsentProvider: React.FC<
  RecordingConsentProviderProps
> = ({ children }) => {
  const [state, setState] = useState<ConsentContextState>({ ready: false });

  const safeWriteToStorage = (consentMap: ConsentMap): void => {
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        const entries = Array.from(consentMap.entries())
          .slice(-5)
          .map(([id, accepted]) => encodeEntry(id, accepted));
        localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(entries));
      }
    } catch (error) {
      console.error("Failed to save consent data to localStorage:", error);
    }
  };

  const touch = (meetingId: string, accepted: boolean): void => {
    if (!state.ready) {
      console.warn("Attempted to touch consent before context is ready");
      return;
    }

    const newMap = new Map(state.consentForMeetings);
    newMap.set(meetingId, accepted);
    safeWriteToStorage(newMap);
    setState({ ready: true, consentForMeetings: newMap });
  };

  const hasAnswered = (meetingId: string): boolean => {
    if (!state.ready) return false;
    return state.consentForMeetings.has(meetingId);
  };

  const hasAccepted = (meetingId: string): boolean => {
    if (!state.ready) return false;
    return state.consentForMeetings.get(meetingId) === true;
  };

  // initialize on mount
  useEffect(() => {
    try {
      if (typeof window === "undefined" || !window.localStorage) {
        setState({ ready: true, consentForMeetings: new Map() });
        return;
      }

      const stored = localStorage.getItem(LOCAL_STORAGE_KEY);
      if (!stored) {
        setState({ ready: true, consentForMeetings: new Map() });
        return;
      }

      const parsed = JSON.parse(stored);
      if (!Array.isArray(parsed)) {
        console.warn("Invalid consent data format in localStorage, resetting");
        setState({ ready: true, consentForMeetings: new Map() });
        return;
      }

      const consentForMeetings = new Map<string, boolean>();
      for (const entry of parsed) {
        const decoded = decodeEntry(entry);
        if (decoded) {
          consentForMeetings.set(decoded.meetingId, decoded.accepted);
        }
      }
      setState({ ready: true, consentForMeetings });
    } catch (error) {
      console.error("Failed to parse consent data from localStorage:", error);
      setState({ ready: true, consentForMeetings: new Map() });
    }
  }, []);

  const value: RecordingConsentContextValue = {
    state,
    touch,
    hasAnswered,
    hasAccepted,
  };

  return (
    <RecordingConsentContext.Provider value={value}>
      {children}
    </RecordingConsentContext.Provider>
  );
};
