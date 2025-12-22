"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { MeetingId } from "./lib/types";

type ConsentMap = Map<MeetingId, boolean>;

type ConsentContextState =
  | { ready: false }
  | {
      ready: true;
      consentForMeetings: ConsentMap;
    };

interface RecordingConsentContextValue {
  state: ConsentContextState;
  touch: (meetingId: MeetingId, accepted: boolean) => void;
  hasAnswered: (meetingId: MeetingId) => boolean;
  hasAccepted: (meetingId: MeetingId) => boolean;
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

const ACCEPTED = "T" as const;
type Accepted = typeof ACCEPTED;
const REJECTED = "F" as const;
type Rejected = typeof REJECTED;
type Consent = Accepted | Rejected;
const SEPARATOR = "|" as const;
type Separator = typeof SEPARATOR;
const DEFAULT_CONSENT = ACCEPTED;
type Entry = `${MeetingId}${Separator}${Consent}`;
type EntryAndDefault = Entry | MeetingId;

// Format: "meetingId|T" or "meetingId|F", legacy format "meetingId" is treated as accepted
const encodeEntry = (meetingId: MeetingId, accepted: boolean): Entry =>
  `${meetingId}|${accepted ? ACCEPTED : REJECTED}`;

const decodeEntry = (
  entry: EntryAndDefault,
): { meetingId: MeetingId; accepted: boolean } | null => {
  const pipeIndex = entry.lastIndexOf(SEPARATOR);
  if (pipeIndex === -1) {
    // Legacy format: no pipe means accepted (backward compat)
    return { meetingId: entry as MeetingId, accepted: true };
  }
  const suffix = entry.slice(pipeIndex + 1);
  const meetingId = entry.slice(0, pipeIndex) as MeetingId;
  // T = accepted, F = rejected, anything else = accepted (safe default)
  const accepted = suffix !== REJECTED;
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

  const touch = (meetingId: MeetingId, accepted: boolean): void => {
    if (!state.ready) {
      console.warn("Attempted to touch consent before context is ready");
      return;
    }

    const newMap = new Map(state.consentForMeetings);
    newMap.set(meetingId, accepted);
    safeWriteToStorage(newMap);
    setState({ ready: true, consentForMeetings: newMap });
  };

  const hasAnswered = (meetingId: MeetingId): boolean => {
    if (!state.ready) return false;
    return state.consentForMeetings.has(meetingId);
  };

  const hasAccepted = (meetingId: MeetingId): boolean => {
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

      const consentForMeetings = new Map<MeetingId, boolean>();
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
