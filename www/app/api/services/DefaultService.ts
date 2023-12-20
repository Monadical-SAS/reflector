/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AudioWaveform } from "../models/AudioWaveform";
import type { Body_transcript_record_upload_v1_transcripts__transcript_id__record_upload_post } from "../models/Body_transcript_record_upload_v1_transcripts__transcript_id__record_upload_post";
import type { CreateParticipant } from "../models/CreateParticipant";
import type { CreateTranscript } from "../models/CreateTranscript";
import type { DeletionStatus } from "../models/DeletionStatus";
import type { GetTranscript } from "../models/GetTranscript";
import type { GetTranscriptTopic } from "../models/GetTranscriptTopic";
import type { GetTranscriptTopicWithWords } from "../models/GetTranscriptTopicWithWords";
import type { GetTranscriptTopicWithWordsPerSpeaker } from "../models/GetTranscriptTopicWithWordsPerSpeaker";
import type { Page_GetTranscript_ } from "../models/Page_GetTranscript_";
import type { Participant } from "../models/Participant";
import type { RtcOffer } from "../models/RtcOffer";
import type { SpeakerAssignment } from "../models/SpeakerAssignment";
import type { SpeakerAssignmentStatus } from "../models/SpeakerAssignmentStatus";
import type { SpeakerMerge } from "../models/SpeakerMerge";
import type { UpdateParticipant } from "../models/UpdateParticipant";
import type { UpdateTranscript } from "../models/UpdateTranscript";
import type { UserInfo } from "../models/UserInfo";

import type { CancelablePromise } from "../core/CancelablePromise";
import { OpenAPI } from "../core/OpenAPI";
import { request as __request } from "../core/request";

export class DefaultService {
  /**
   * Metrics
   * Endpoint that serves Prometheus metrics.
   * @returns any Successful Response
   * @throws ApiError
   */
  public static metrics(): CancelablePromise<any> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/metrics",
    });
  }

  /**
   * Transcripts List
   * @param page Page number
   * @param size Page size
   * @returns Page_GetTranscript_ Successful Response
   * @throws ApiError
   */
  public static v1TranscriptsList(
    page: number = 1,
    size: number = 50,
  ): CancelablePromise<Page_GetTranscript_> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/v1/transcripts",
      query: {
        page: page,
        size: size,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }

  /**
   * Transcripts Create
   * @param requestBody
   * @returns GetTranscript Successful Response
   * @throws ApiError
   */
  public static v1TranscriptsCreate(
    requestBody: CreateTranscript,
  ): CancelablePromise<GetTranscript> {
    return __request(OpenAPI, {
      method: "POST",
      url: "/v1/transcripts",
      body: requestBody,
      mediaType: "application/json",
      errors: {
        422: `Validation Error`,
      },
    });
  }

  /**
   * Transcript Get
   * @param transcriptId
   * @returns GetTranscript Successful Response
   * @throws ApiError
   */
  public static v1TranscriptGet(
    transcriptId: string,
  ): CancelablePromise<GetTranscript> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/v1/transcripts/{transcript_id}",
      path: {
        transcript_id: transcriptId,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }

  /**
   * Transcript Update
   * @param transcriptId
   * @param requestBody
   * @returns GetTranscript Successful Response
   * @throws ApiError
   */
  public static v1TranscriptUpdate(
    transcriptId: string,
    requestBody: UpdateTranscript,
  ): CancelablePromise<GetTranscript> {
    return __request(OpenAPI, {
      method: "PATCH",
      url: "/v1/transcripts/{transcript_id}",
      path: {
        transcript_id: transcriptId,
      },
      body: requestBody,
      mediaType: "application/json",
      errors: {
        422: `Validation Error`,
      },
    });
  }

  /**
   * Transcript Delete
   * @param transcriptId
   * @returns DeletionStatus Successful Response
   * @throws ApiError
   */
  public static v1TranscriptDelete(
    transcriptId: string,
  ): CancelablePromise<DeletionStatus> {
    return __request(OpenAPI, {
      method: "DELETE",
      url: "/v1/transcripts/{transcript_id}",
      path: {
        transcript_id: transcriptId,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }

  /**
   * Transcript Get Topics
   * @param transcriptId
   * @returns GetTranscriptTopic Successful Response
   * @throws ApiError
   */
  public static v1TranscriptGetTopics(
    transcriptId: string,
  ): CancelablePromise<Array<GetTranscriptTopic>> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/v1/transcripts/{transcript_id}/topics",
      path: {
        transcript_id: transcriptId,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }

  /**
   * Transcript Get Topics With Words
   * @param transcriptId
   * @returns GetTranscriptTopicWithWords Successful Response
   * @throws ApiError
   */
  public static v1TranscriptGetTopicsWithWords(
    transcriptId: string,
  ): CancelablePromise<Array<GetTranscriptTopicWithWords>> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/v1/transcripts/{transcript_id}/topics/with-words",
      path: {
        transcript_id: transcriptId,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }

  /**
   * Transcript Get Topics With Words Per Speaker
   * @param transcriptId
   * @param topicId
   * @returns GetTranscriptTopicWithWordsPerSpeaker Successful Response
   * @throws ApiError
   */
  public static v1TranscriptGetTopicsWithWordsPerSpeaker(
    transcriptId: string,
    topicId: string,
  ): CancelablePromise<GetTranscriptTopicWithWordsPerSpeaker> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/v1/transcripts/{transcript_id}/topics/{topic_id}/words-per-speaker",
      path: {
        transcript_id: transcriptId,
        topic_id: topicId,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }

  /**
   * Transcript Get Audio Mp3
   * @param transcriptId
   * @param token
   * @returns any Successful Response
   * @throws ApiError
   */
  public static v1TranscriptHeadAudioMp3(
    transcriptId: string,
    token?: string | null,
  ): CancelablePromise<any> {
    return __request(OpenAPI, {
      method: "HEAD",
      url: "/v1/transcripts/{transcript_id}/audio/mp3",
      path: {
        transcript_id: transcriptId,
      },
      query: {
        token: token,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }

  /**
   * Transcript Get Audio Mp3
   * @param transcriptId
   * @param token
   * @returns any Successful Response
   * @throws ApiError
   */
  public static v1TranscriptGetAudioMp3(
    transcriptId: string,
    token?: string | null,
  ): CancelablePromise<any> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/v1/transcripts/{transcript_id}/audio/mp3",
      path: {
        transcript_id: transcriptId,
      },
      query: {
        token: token,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }

  /**
   * Transcript Get Audio Waveform
   * @param transcriptId
   * @returns AudioWaveform Successful Response
   * @throws ApiError
   */
  public static v1TranscriptGetAudioWaveform(
    transcriptId: string,
  ): CancelablePromise<AudioWaveform> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/v1/transcripts/{transcript_id}/audio/waveform",
      path: {
        transcript_id: transcriptId,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }

  /**
   * Transcript Get Participants
   * @param transcriptId
   * @returns Participant Successful Response
   * @throws ApiError
   */
  public static v1TranscriptGetParticipants(
    transcriptId: string,
  ): CancelablePromise<Array<Participant>> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/v1/transcripts/{transcript_id}/participants",
      path: {
        transcript_id: transcriptId,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }

  /**
   * Transcript Add Participant
   * @param transcriptId
   * @param requestBody
   * @returns Participant Successful Response
   * @throws ApiError
   */
  public static v1TranscriptAddParticipant(
    transcriptId: string,
    requestBody: CreateParticipant,
  ): CancelablePromise<Participant> {
    return __request(OpenAPI, {
      method: "POST",
      url: "/v1/transcripts/{transcript_id}/participants",
      path: {
        transcript_id: transcriptId,
      },
      body: requestBody,
      mediaType: "application/json",
      errors: {
        422: `Validation Error`,
      },
    });
  }

  /**
   * Transcript Get Participant
   * @param transcriptId
   * @param participantId
   * @returns Participant Successful Response
   * @throws ApiError
   */
  public static v1TranscriptGetParticipant(
    transcriptId: string,
    participantId: string,
  ): CancelablePromise<Participant> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/v1/transcripts/{transcript_id}/participants/{participant_id}",
      path: {
        transcript_id: transcriptId,
        participant_id: participantId,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }

  /**
   * Transcript Update Participant
   * @param transcriptId
   * @param participantId
   * @param requestBody
   * @returns Participant Successful Response
   * @throws ApiError
   */
  public static v1TranscriptUpdateParticipant(
    transcriptId: string,
    participantId: string,
    requestBody: UpdateParticipant,
  ): CancelablePromise<Participant> {
    return __request(OpenAPI, {
      method: "PATCH",
      url: "/v1/transcripts/{transcript_id}/participants/{participant_id}",
      path: {
        transcript_id: transcriptId,
        participant_id: participantId,
      },
      body: requestBody,
      mediaType: "application/json",
      errors: {
        422: `Validation Error`,
      },
    });
  }

  /**
   * Transcript Delete Participant
   * @param transcriptId
   * @param participantId
   * @returns DeletionStatus Successful Response
   * @throws ApiError
   */
  public static v1TranscriptDeleteParticipant(
    transcriptId: string,
    participantId: string,
  ): CancelablePromise<DeletionStatus> {
    return __request(OpenAPI, {
      method: "DELETE",
      url: "/v1/transcripts/{transcript_id}/participants/{participant_id}",
      path: {
        transcript_id: transcriptId,
        participant_id: participantId,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }

  /**
   * Transcript Assign Speaker
   * @param transcriptId
   * @param requestBody
   * @returns SpeakerAssignmentStatus Successful Response
   * @throws ApiError
   */
  public static v1TranscriptAssignSpeaker(
    transcriptId: string,
    requestBody: SpeakerAssignment,
  ): CancelablePromise<SpeakerAssignmentStatus> {
    return __request(OpenAPI, {
      method: "PATCH",
      url: "/v1/transcripts/{transcript_id}/speaker/assign",
      path: {
        transcript_id: transcriptId,
      },
      body: requestBody,
      mediaType: "application/json",
      errors: {
        422: `Validation Error`,
      },
    });
  }

  /**
   * Transcript Merge Speaker
   * @param transcriptId
   * @param requestBody
   * @returns SpeakerAssignmentStatus Successful Response
   * @throws ApiError
   */
  public static v1TranscriptMergeSpeaker(
    transcriptId: string,
    requestBody: SpeakerMerge,
  ): CancelablePromise<SpeakerAssignmentStatus> {
    return __request(OpenAPI, {
      method: "PATCH",
      url: "/v1/transcripts/{transcript_id}/speaker/merge",
      path: {
        transcript_id: transcriptId,
      },
      body: requestBody,
      mediaType: "application/json",
      errors: {
        422: `Validation Error`,
      },
    });
  }

  /**
   * Transcript Record Upload
   * @param transcriptId
   * @param formData
   * @returns any Successful Response
   * @throws ApiError
   */
  public static v1TranscriptRecordUpload(
    transcriptId: string,
    formData: Body_transcript_record_upload_v1_transcripts__transcript_id__record_upload_post,
  ): CancelablePromise<any> {
    return __request(OpenAPI, {
      method: "POST",
      url: "/v1/transcripts/{transcript_id}/record/upload",
      path: {
        transcript_id: transcriptId,
      },
      formData: formData,
      mediaType: "multipart/form-data",
      errors: {
        422: `Validation Error`,
      },
    });
  }

  /**
   * Transcript Get Websocket Events
   * @param transcriptId
   * @returns any Successful Response
   * @throws ApiError
   */
  public static v1TranscriptGetWebsocketEvents(
    transcriptId: string,
  ): CancelablePromise<any> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/v1/transcripts/{transcript_id}/events",
      path: {
        transcript_id: transcriptId,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }

  /**
   * Transcript Record Webrtc
   * @param transcriptId
   * @param requestBody
   * @returns any Successful Response
   * @throws ApiError
   */
  public static v1TranscriptRecordWebrtc(
    transcriptId: string,
    requestBody: RtcOffer,
  ): CancelablePromise<any> {
    return __request(OpenAPI, {
      method: "POST",
      url: "/v1/transcripts/{transcript_id}/record/webrtc",
      path: {
        transcript_id: transcriptId,
      },
      body: requestBody,
      mediaType: "application/json",
      errors: {
        422: `Validation Error`,
      },
    });
  }

  /**
   * User Me
   * @returns any Successful Response
   * @throws ApiError
   */
  public static v1UserMe(): CancelablePromise<UserInfo | null> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/v1/me",
    });
  }
}
