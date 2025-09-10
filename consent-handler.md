# Recording Consent Handler Documentation

This document describes the recording consent functionality found in the main branch of Reflector.

## Overview

The recording consent system manages user consent for storing meeting audio recordings on servers. It only appears when `recording_type` is set to "cloud" and shows a prominent blue button with toast-based consent dialog.

## Components and Files

### 1. ConsentDialogButton Component

**Location**: `www/app/[roomName]/page.tsx:206-234`

**Visual Appearance**:
- **Button text**: "Meeting is being recorded"
- **Button color**: Blue (`colorPalette="blue"`)
- **Position**: Absolute positioned at `top="56px"` `left="8px"`
- **Z-index**: 1000 (appears above video)
- **Size**: Small (`size="sm"`)
- **Icon**: FaBars icon from react-icons/fa6

**Behavior**:
- Only shows when:
  - Consent context is ready
  - User hasn't already given consent for this meeting
  - Not currently loading consent submission
  - Recording type requires consent (cloud recording)

### 2. Consent Modal/Toast

**Location**: `www/app/[roomName]/page.tsx:107-196` (useConsentDialog hook)

**Visual Appearance**:
- **Background**: Semi-transparent white (`bg="rgba(255, 255, 255, 0.7)"`)
- **Border radius**: Large (`borderRadius="lg"`)
- **Box shadow**: Large (`boxShadow="lg"`)
- **Max width**: Medium (`maxW="md"`)
- **Position**: Top placement toast

**Content**:
- **Main text**: "Can we have your permission to store this meeting's audio recording on our servers?"
- **Font**: Medium size, medium weight, center aligned

**Buttons**:
1. **Decline Button**:
   - Text: "No, delete after transcription"
   - Style: Ghost variant, small size
   - Action: Sets consent to false

2. **Accept Button**:
   - Text: "Yes, store the audio"
   - Style: Primary color palette, small size
   - Action: Sets consent to true
   - Has special focus management for accessibility

### 3. Recording Consent Context

**Location**: `www/app/recordingConsentContext.tsx`

**Key Features**:
- Uses localStorage to persist consent decisions
- Keeps track of up to 5 recent meeting consent decisions
- Provides three main functions:
  - `state`: Current context state (ready/not ready + consent set)
  - `touch(meetingId)`: Mark consent as given for a meeting
  - `hasConsent(meetingId)`: Check if consent already given

**localStorage Key**: `"recording_consent_meetings"`

### 4. Focus Management

**Location**: `www/app/[roomName]/page.tsx:39-74` (useConsentWherebyFocusManagement hook)

**Purpose**: Manages focus between the consent button and Whereby video embed for accessibility
- Initially focuses the accept button
- Handles Whereby "ready" events to refocus consent
- Restores original focus when consent dialog closes

### 5. API Integration

**Hook**: `useMeetingAudioConsent()` from `../lib/apiHooks`

**Endpoint**: Submits consent decision to `/meetings/{meeting_id}/consent` with body:
```json
{
  "consent_given": boolean
}
```

## Logic Flow

1. **Trigger Condition**:
   - Meeting has `recording_type === "cloud"`
   - User hasn't already consented for this meeting

2. **Button Display**:
   - Blue "Meeting is being recorded" button appears over video

3. **User Interaction**:
   - Click button → Opens consent toast modal
   - User chooses "Yes" or "No"
   - Decision sent to API
   - Meeting ID added to local consent cache
   - Modal closes

4. **State Management**:
   - Consent decision cached locally for this meeting
   - Button disappears after consent given
   - No further prompts for this meeting

## Integration Points

- **Room Component**: Main integration in `www/app/[roomName]/page.tsx:324-329`
- **Conditional Rendering**: Only shows when `recordingTypeRequiresConsent(recordingType)` returns true
- **Authentication**: Requires user to be authenticated
- **Whereby Integration**: Coordinates with video embed focus management

## Key Features

- **Non-blocking**: User can interact with video while consent prompt is visible
- **Persistent**: Consent decisions remembered across sessions
- **Accessible**: Proper focus management and keyboard navigation
- **Conditional**: Only appears for cloud recordings requiring consent
- **Toast-based**: Uses toast system for non-intrusive user experience