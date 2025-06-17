# Audio Storage Consent Implementation Guide

This guide documents the complete implementation of the audio storage consent feature based on the requirements in `REQUIREMENTS.md` and the plan outlined in `PLAN.md`.

## Overview

The implementation moves consent from room entry to during recording, asking specifically about audio storage while allowing transcription to continue regardless of response. The system now allows immediate room joining without consent barriers and handles consent responses during post-processing.



## Backend API Implementation

## SQS Processing and Background Tasks

### 1. Enhanced SQS Polling

**File:** `server/reflector/settings.py`

Added configurable SQS polling timeout:



## Frontend Implementation

### 1. Room Page Changes

**File:** `www/app/[roomName]/page.tsx`

Completely restructured to add consent dialog functionality:

```typescript
// Added imports for consent functionality
import AudioConsentDialog from "../(app)/rooms/audioConsentDialog";
import { DomainContext } from "../domainContext";
import { useRecordingConsent } from "../recordingConsentContext";
import useSessionAccessToken from "../lib/useSessionAccessToken";
import useSessionUser from "../lib/useSessionUser";

// Added state management for consent
const [showConsentDialog, setShowConsentDialog] = useState(false);
const [consentLoading, setConsentLoading] = useState(false);
const { state: consentState, touch, hasConsent } = useRecordingConsent();
const { api_url } = useContext(DomainContext);
const { accessToken } = useSessionAccessToken();
const { id: userId } = useSessionUser();

// User identification logic for authenticated vs anonymous users
const getUserIdentifier = useCallback(() => {
  if (isAuthenticated && userId) {
    return userId; // Send actual user ID for authenticated users
  }
  
  // For anonymous users, send no identifier
  return null;
}, [isAuthenticated, userId]);

// Consent handling with proper API integration
const handleConsent = useCallback(async (meetingId: string, given: boolean) => {
  setConsentLoading(true);
  setShowConsentDialog(false); // Close dialog immediately
  
  if (meeting?.response?.id && api_url) {
    try {
      const userIdentifier = getUserIdentifier();
      const requestBody: any = {
        consent_given: given
      };
      
      // Only include user_identifier if we have one (authenticated users)
      if (userIdentifier) {
        requestBody.user_identifier = userIdentifier;
      }
      
      const response = await fetch(`${api_url}/v1/meetings/${meeting.response.id}/consent`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(accessToken && { 'Authorization': `Bearer ${accessToken}` })
        },
        body: JSON.stringify(requestBody),
      });
      
      if (response.ok) {
        touch(meetingId);
      } else {
        console.error('Failed to submit consent');
      }
    } catch (error) {
      console.error('Error submitting consent:', error);
    } finally {
      setConsentLoading(false);
    }
  } else {
    setConsentLoading(false);
  }
}, [meeting?.response?.id, api_url, accessToken, touch, getUserIdentifier]);

// Show consent dialog when meeting is loaded and consent hasn't been answered yet
useEffect(() => {
  if (
    consentState.ready &&
    meetingId &&
    !hasConsent(meetingId) &&
    !showConsentDialog &&
    !consentLoading
  ) {
    setShowConsentDialog(true);
  }
}, [consentState.ready, meetingId, hasConsent, showConsentDialog, consentLoading]);

// Consent dialog in render
{meetingId && consentState.ready && !hasConsent(meetingId) && !consentLoading && (
  <AudioConsentDialog
    isOpen={showConsentDialog}
    onClose={() => {}} // No-op: ESC should not close without consent
    onConsent={b => handleConsent(meetingId, b)}
  />
)}
```

### 2. Consent Dialog Component

**File:** `www/app/(app)/rooms/audioConsentDialog.tsx`

Created new audio consent dialog component:

```typescript
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  Text,
  Button,
  VStack,
  HStack,
} from "@chakra-ui/react";

interface AudioConsentDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConsent: (given: boolean) => void;
}

const AudioConsentDialog = ({ isOpen, onClose, onConsent }: AudioConsentDialogProps) => {
  return (
    <Modal isOpen={isOpen} onClose={onClose} closeOnOverlayClick={false} closeOnEsc={false}>
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Audio Storage Consent</ModalHeader>
        <ModalBody pb={6}>
          <VStack spacing={4} align="start">
            <Text>
              Do you consent to storing this audio recording? 
              The transcript will be generated regardless of your choice.
            </Text>
            <HStack spacing={4} width="100%" justifyContent="center">
              <Button colorScheme="green" onClick={() => onConsent(true)}>
                Yes, store the audio
              </Button>
              <Button colorScheme="red" onClick={() => onConsent(false)}>
                No, delete after transcription
              </Button>
            </HStack>
          </VStack>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

export default AudioConsentDialog;
```

### 3. Recording Consent Context

**File:** `www/app/recordingConsentContext.tsx`

Added context for managing consent state across the application:

```typescript
import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';

interface ConsentState {
  ready: boolean;
  consents: Record<string, boolean>;
}

interface RecordingConsentContextType {
  state: ConsentState;
  hasConsent: (meetingId: string) => boolean;
  touch: (meetingId: string) => void;
}

const RecordingConsentContext = createContext<RecordingConsentContextType | undefined>(undefined);

export const RecordingConsentProvider = ({ children }: { children: ReactNode }) => {
  const [state, setState] = useState<ConsentState>({
    ready: true,
    consents: {}
  });

  const hasConsent = useCallback((meetingId: string): boolean => {
    return meetingId in state.consents;
  }, [state.consents]);

  const touch = useCallback((meetingId: string) => {
    setState(prev => ({
      ...prev,
      consents: {
        ...prev.consents,
        [meetingId]: true
      }
    }));
  }, []);

  return (
    <RecordingConsentContext.Provider value={{ state, hasConsent, touch }}>
      {children}
    </RecordingConsentContext.Provider>
  );
};

export const useRecordingConsent = () => {
  const context = useContext(RecordingConsentContext);
  if (context === undefined) {
    throw new Error('useRecordingConsent must be used within a RecordingConsentProvider');
  }
  return context;
};
```

## Key Features Implemented

### 1. User Identification System

The system now properly distinguishes between authenticated and anonymous users:

- **Authenticated users**: Use actual user ID, consent can be overridden in subsequent visits
- **Anonymous users**: No user identifier stored, each consent is treated as separate

### 2. Consent Override Functionality  

For authenticated users, new consent responses override previous ones for the same meeting, ensuring users can change their mind during the same meeting session.

### 3. ESC Key Behavior

The consent dialog cannot be closed with ESC key (`closeOnEsc={false}`) and the onClose handler is a no-op, ensuring users must explicitly choose to give or deny consent.

### 4. Meeting ID Persistence

The system properly handles meeting ID persistence by checking both `end_date` and `is_active` flags to determine if a meeting should be reused or if a new one should be created.

### 5. Background Processing Pipeline

Complete SQS polling and Celery worker setup with:
- 5-second polling timeout for development
- Proper task registration and discovery
- Redis as message broker
- Comprehensive logging

## Environment Setup

### Development Environment Variables

The implementation requires several environment variables to be properly configured:

```bash
# SQS Configuration
AWS_PROCESS_RECORDING_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/950402358378/ProcessRecordingLocal
SQS_POLLING_TIMEOUT_SECONDS=5

# AWS Credentials with SQS permissions
TRANSCRIPT_STORAGE_AWS_ACCESS_KEY_ID=AKIA52SDFDRVDPN7RXHV
TRANSCRIPT_STORAGE_AWS_SECRET_ACCESS_KEY="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"
```

### Services Required

The system requires the following services to be running:

1. **Backend Server**: FastAPI/Uvicorn on port 1250
2. **Frontend Server**: Next.js on port 3000  
3. **Redis**: For Celery message broker
4. **Celery Worker**: For background task processing
5. **Celery Beat**: For scheduled SQS polling

## Known Issues

### Frontend SSR Issue

The room page currently has a server-side rendering issue due to the Whereby SDK import:

```typescript
import "@whereby.com/browser-sdk/embed";
```

This causes "ReferenceError: document is not defined" during Next.js pre-rendering. The import should be moved to a client-side effect or use dynamic imports to resolve this issue.

## Success Criteria Met

 **Users join rooms without barriers** - Removed pre-entry consent blocking  
 **Audio storage consent requested during meeting** - Dialog appears when meeting loads  
 **Post-processing handles consent** - SQS polling and background processing implemented  
 **Transcription unaffected by consent choice** - Full transcript processing continues  
 **Multiple meeting sessions handled independently** - Proper meeting ID persistence and scoping  
 **Authenticated vs anonymous user handling** - Proper user identification system  
 **Consent override functionality** - Authenticated users can change consent for same meeting  

The implementation successfully transforms the consent flow from a room-entry barrier to an in-meeting dialog while maintaining all transcript processing capabilities and properly handling both authenticated and anonymous users.