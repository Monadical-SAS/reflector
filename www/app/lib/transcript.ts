import { components } from "../reflector-api";

type ApiTranscriptStatus =
  components["schemas"]["GetTranscriptWithParticipants"]["status"];

export type TranscriptStatus = ApiTranscriptStatus;
