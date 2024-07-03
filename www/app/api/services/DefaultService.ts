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
import type { BaseHttpRequest } from "../core/BaseHttpRequest";

export type TDataV1TranscriptsList = {
  /**
   * Page number
   */
  page?: number;
  /**
   * Page size
   */
  size?: number;
};
export type TDataV1TranscriptsCreate = {
  requestBody: CreateTranscript;
};
export type TDataV1TranscriptGet = {
  transcriptId: string;
};
export type TDataV1TranscriptUpdate = {
  requestBody: UpdateTranscript;
  transcriptId: string;
};
export type TDataV1TranscriptDelete = {
  transcriptId: string;
};
export type TDataV1TranscriptGetTopics = {
  transcriptId: string;
};
export type TDataV1TranscriptGetTopicsWithWords = {
  transcriptId: string;
};
export type TDataV1TranscriptGetTopicsWithWordsPerSpeaker = {
  topicId: string;
  transcriptId: string;
};
export type TDataV1TranscriptHeadAudioMp3 = {
  token?: string | null;
  transcriptId: string;
};
export type TDataV1TranscriptGetAudioMp3 = {
  token?: string | null;
  transcriptId: string;
};
export type TDataV1TranscriptGetAudioWaveform = {
  transcriptId: string;
};
export type TDataV1TranscriptGetParticipants = {
  transcriptId: string;
};
export type TDataV1TranscriptAddParticipant = {
  requestBody: CreateParticipant;
  transcriptId: string;
};
export type TDataV1TranscriptGetParticipant = {
  participantId: string;
  transcriptId: string;
};
export type TDataV1TranscriptUpdateParticipant = {
  participantId: string;
  requestBody: UpdateParticipant;
  transcriptId: string;
};
export type TDataV1TranscriptDeleteParticipant = {
  participantId: string;
  transcriptId: string;
};
export type TDataV1TranscriptAssignSpeaker = {
  requestBody: SpeakerAssignment;
  transcriptId: string;
};
export type TDataV1TranscriptMergeSpeaker = {
  requestBody: SpeakerMerge;
  transcriptId: string;
};
export type TDataV1TranscriptRecordUpload = {
  formData: Body_transcript_record_upload_v1_transcripts__transcript_id__record_upload_post;
  transcriptId: string;
};
export type TDataV1TranscriptGetWebsocketEvents = {
  transcriptId: string;
};
export type TDataV1TranscriptRecordWebrtc = {
  requestBody: RtcOffer;
  transcriptId: string;
};

export class DefaultService {
  constructor(public readonly httpRequest: BaseHttpRequest) {}

  /**
   * Metrics
   * Endpoint that serves Prometheus metrics.
   * @returns unknown Successful Response
   * @throws ApiError
   */
  public metrics(): CancelablePromise<unknown> {
    return this.httpRequest.request({
      method: "GET",
      url: "/metrics",
    });
  }

  /**
   * Transcripts List
   * @returns Page_GetTranscript_ Successful Response
   * @throws ApiError
   */
  public v1TranscriptsList(
    data: TDataV1TranscriptsList = {},
  ): CancelablePromise<Page_GetTranscript_> {
    const { page = 1, size = 50 } = data;
    return this.httpRequest.request({
      method: "GET",
      url: "/v1/transcripts",
      query: {
        page,
        size,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }

  /**
   * Transcripts Create
   * @returns GetTranscript Successful Response
   * @throws ApiError
   */
  public v1TranscriptsCreate(
    data: TDataV1TranscriptsCreate,
  ): CancelablePromise<GetTranscript> {
    const { requestBody } = data;
    return this.httpRequest.request({
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
   * @returns GetTranscript Successful Response
   * @throws ApiError
   */
  public v1TranscriptGet(
    data: TDataV1TranscriptGet,
  ): CancelablePromise<GetTranscript> {
    const { transcriptId } = data;
    return this.httpRequest.request({
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
   * @returns GetTranscript Successful Response
   * @throws ApiError
   */
  public v1TranscriptUpdate(
    data: TDataV1TranscriptUpdate,
  ): CancelablePromise<GetTranscript> {
    const { requestBody, transcriptId } = data;
    return this.httpRequest.request({
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
   * @returns DeletionStatus Successful Response
   * @throws ApiError
   */
  public v1TranscriptDelete(
    data: TDataV1TranscriptDelete,
  ): CancelablePromise<DeletionStatus> {
    const { transcriptId } = data;
    return this.httpRequest.request({
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
   * @returns GetTranscriptTopic Successful Response
   * @throws ApiError
   */
  public v1TranscriptGetTopics(
    data: TDataV1TranscriptGetTopics,
  ): CancelablePromise<Array<GetTranscriptTopic>> {
    const { transcriptId } = data;
    return this.httpRequest.request({
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
   * @returns GetTranscriptTopicWithWords Successful Response
   * @throws ApiError
   */
  public v1TranscriptGetTopicsWithWords(
    data: TDataV1TranscriptGetTopicsWithWords,
  ): CancelablePromise<Array<GetTranscriptTopicWithWords>> {
    const { transcriptId } = data;
    return this.httpRequest.request({
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
   * @returns GetTranscriptTopicWithWordsPerSpeaker Successful Response
   * @throws ApiError
   */
  public v1TranscriptGetTopicsWithWordsPerSpeaker(
    data: TDataV1TranscriptGetTopicsWithWordsPerSpeaker,
  ): CancelablePromise<GetTranscriptTopicWithWordsPerSpeaker> {
    const { topicId, transcriptId } = data;
    return this.httpRequest.request({
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
   * @returns unknown Successful Response
   * @throws ApiError
   */
  public v1TranscriptHeadAudioMp3(
    data: TDataV1TranscriptHeadAudioMp3,
  ): CancelablePromise<unknown> {
    const { token, transcriptId } = data;
    return this.httpRequest.request({
      method: "HEAD",
      url: "/v1/transcripts/{transcript_id}/audio/mp3",
      path: {
        transcript_id: transcriptId,
      },
      query: {
        token,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }

  /**
   * Transcript Get Audio Mp3
   * @returns unknown Successful Response
   * @throws ApiError
   */
  public v1TranscriptGetAudioMp3(
    data: TDataV1TranscriptGetAudioMp3,
  ): CancelablePromise<unknown> {
    const { token, transcriptId } = data;
    return this.httpRequest.request({
      method: "GET",
      url: "/v1/transcripts/{transcript_id}/audio/mp3",
      path: {
        transcript_id: transcriptId,
      },
      query: {
        token,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }

  /**
   * Transcript Get Audio Waveform
   * @returns AudioWaveform Successful Response
   * @throws ApiError
   */
  public v1TranscriptGetAudioWaveform(
    data: TDataV1TranscriptGetAudioWaveform,
  ): CancelablePromise<AudioWaveform> {
    const { transcriptId } = data;
    return this.httpRequest.request({
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
   * @returns Participant Successful Response
   * @throws ApiError
   */
  public v1TranscriptGetParticipants(
    data: TDataV1TranscriptGetParticipants,
  ): CancelablePromise<Array<Participant>> {
    const { transcriptId } = data;
    return this.httpRequest.request({
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
   * @returns Participant Successful Response
   * @throws ApiError
   */
  public v1TranscriptAddParticipant(
    data: TDataV1TranscriptAddParticipant,
  ): CancelablePromise<Participant> {
    const { requestBody, transcriptId } = data;
    return this.httpRequest.request({
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
   * @returns Participant Successful Response
   * @throws ApiError
   */
  public v1TranscriptGetParticipant(
    data: TDataV1TranscriptGetParticipant,
  ): CancelablePromise<Participant> {
    const { participantId, transcriptId } = data;
    return this.httpRequest.request({
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
   * @returns Participant Successful Response
   * @throws ApiError
   */
  public v1TranscriptUpdateParticipant(
    data: TDataV1TranscriptUpdateParticipant,
  ): CancelablePromise<Participant> {
    const { participantId, requestBody, transcriptId } = data;
    return this.httpRequest.request({
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
   * @returns DeletionStatus Successful Response
   * @throws ApiError
   */
  public v1TranscriptDeleteParticipant(
    data: TDataV1TranscriptDeleteParticipant,
  ): CancelablePromise<DeletionStatus> {
    const { participantId, transcriptId } = data;
    return this.httpRequest.request({
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
   * @returns SpeakerAssignmentStatus Successful Response
   * @throws ApiError
   */
  public v1TranscriptAssignSpeaker(
    data: TDataV1TranscriptAssignSpeaker,
  ): CancelablePromise<SpeakerAssignmentStatus> {
    const { requestBody, transcriptId } = data;
    return this.httpRequest.request({
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
   * @returns SpeakerAssignmentStatus Successful Response
   * @throws ApiError
   */
  public v1TranscriptMergeSpeaker(
    data: TDataV1TranscriptMergeSpeaker,
  ): CancelablePromise<SpeakerAssignmentStatus> {
    const { requestBody, transcriptId } = data;
    return this.httpRequest.request({
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
   * @returns unknown Successful Response
   * @throws ApiError
   */
  public v1TranscriptRecordUpload(
    data: TDataV1TranscriptRecordUpload,
  ): CancelablePromise<unknown> {
    const { formData, transcriptId } = data;
    return this.httpRequest.request({
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
   * @returns unknown Successful Response
   * @throws ApiError
   */
  public v1TranscriptGetWebsocketEvents(
    data: TDataV1TranscriptGetWebsocketEvents,
  ): CancelablePromise<unknown> {
    const { transcriptId } = data;
    return this.httpRequest.request({
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
   * @returns unknown Successful Response
   * @throws ApiError
   */
  public v1TranscriptRecordWebrtc(
    data: TDataV1TranscriptRecordWebrtc,
  ): CancelablePromise<unknown> {
    const { requestBody, transcriptId } = data;
    return this.httpRequest.request({
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
   * @returns unknown Successful Response
   * @throws ApiError
   */
  public v1UserMe(): CancelablePromise<UserInfo | null> {
    return this.httpRequest.request({
      method: "GET",
      url: "/v1/me",
    });
  }
}
