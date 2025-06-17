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

export const RecordingConsentProvider: React.FC<RecordingConsentProviderProps> = ({ children }) => {
  const [state, setState] = useState<ConsentContextState>({ ready: false });

  const safeWriteToStorage = (meetingIds: string[]): void => {
    try {
      localStorage.setItem("recording_consent_meetings", JSON.stringify(meetingIds));
    } catch (error) {
      console.error("Failed to save consent data to localStorage:", error);
    }
  };

  const touch = (meetingId: string): void => {
    
    if (!state.ready) {
      console.warn("Attempted to touch consent before context is ready");
      return;
    }

    // Update context state (always works)
    const newSet = new Set([...state.consentAnsweredForMeetings, meetingId]);
    
    const array = Array.from(newSet).slice(-5); // Keep latest 5
    safeWriteToStorage(array);
    
    // Update state regardless of storage success
    setState({ ready: true, consentAnsweredForMeetings: newSet });
  };

  const hasConsent = (meetingId: string): boolean => {
    if (!state.ready) return false;
    return state.consentAnsweredForMeetings.has(meetingId);
  };

  // Initialize from localStorage on mount (client-side only)
  useEffect(() => {
    try {
      const stored = localStorage.getItem("recording_consent_meetings");
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
      
      const consentAnsweredForMeetings = new Set(parsed.filter(id => typeof id === 'string'));
      setState({ ready: true, consentAnsweredForMeetings });
    } catch (error) {
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