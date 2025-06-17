"use client";

import React, { createContext, useContext, useEffect, useState } from "react";

type ConsentContextState = 
  | { ready: false }
  | { 
      ready: true, 
      consentAnsweredForMeetings: Set<string> 
    };

interface RecordingConsentContextValue {
  state: ConsentContextState;
  touch: (meetingId: string) => void;
  hasConsent: (meetingId: string) => boolean;
}

const RecordingConsentContext = createContext<RecordingConsentContextValue | undefined>(undefined);

export const useRecordingConsent = () => {
  const context = useContext(RecordingConsentContext);
  if (!context) {
    throw new Error("useRecordingConsent must be used within RecordingConsentProvider");
  }
  return context;
};

interface RecordingConsentProviderProps {
  children: React.ReactNode;
}

const LOCAL_STORAGE_KEY = "recording_consent_meetings";

export const RecordingConsentProvider: React.FC<RecordingConsentProviderProps> = ({ children }) => {
  const [state, setState] = useState<ConsentContextState>({ ready: false });

  const safeWriteToStorage = (meetingIds: string[]): void => {
    try {
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(meetingIds));
    } catch (error) {
      console.error("Failed to save consent data to localStorage:", error);
    }
  };

  // writes to local storage and to the state of context both
  const touch = (meetingId: string): void => {
    
    if (!state.ready) {
      console.warn("Attempted to touch consent before context is ready");
      return;
    }

    // has success regardless local storage write success: we don't handle that
    // and don't want to crash anything with just consent functionality
    const newSet = state.consentAnsweredForMeetings.has(meetingId) ?
      state.consentAnsweredForMeetings :
      new Set([...state.consentAnsweredForMeetings, meetingId]);
    // note: preserves the set insertion order
    const array = Array.from(newSet).slice(-5); // Keep latest 5
    safeWriteToStorage(array);
    setState({ ready: true, consentAnsweredForMeetings: newSet });
  };

  const hasConsent = (meetingId: string): boolean => {
    if (!state.ready) return false;
    return state.consentAnsweredForMeetings.has(meetingId);
  };

  // initialize on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(LOCAL_STORAGE_KEY);
      if (!stored) {
        setState({ ready: true, consentAnsweredForMeetings: new Set() });
        return;
      }
      
      const parsed = JSON.parse(stored);
      if (!Array.isArray(parsed)) {
        console.warn("Invalid consent data format in localStorage, resetting");
        setState({ ready: true, consentAnsweredForMeetings: new Set() });
        return;
      }

      // pre-historic way of parsing!
      const consentAnsweredForMeetings = new Set(parsed.filter(id => !!id && typeof id === 'string'));
      setState({ ready: true, consentAnsweredForMeetings });
    } catch (error) {
      // we don't want to fail the page here; the component is not essential.
      console.error("Failed to parse consent data from localStorage:", error);
      setState({ ready: true, consentAnsweredForMeetings: new Set() });
    }
  }, []);

  const value: RecordingConsentContextValue = {
    state,
    touch,
    hasConsent,
  };

  return (
    <RecordingConsentContext.Provider value={value}>
      {children}
    </RecordingConsentContext.Provider>
  );
};