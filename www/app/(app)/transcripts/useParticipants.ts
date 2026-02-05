import type { components } from "../../reflector-api";
type Participant = components["schemas"]["Participant"];
import { useTranscriptParticipants } from "../../lib/apiHooks";
import { parseMaybeNonEmptyString } from "../../lib/utils";

type ErrorParticipants = {
  error: Error;
  loading: false;
  response: null;
};

type LoadingParticipants = {
  response: Participant[] | null;
  loading: true;
  error: null;
};

type SuccessParticipants = {
  response: Participant[];
  loading: boolean;
  error: null;
};

export type UseParticipants = (
  | ErrorParticipants
  | LoadingParticipants
  | SuccessParticipants
) & { refetch: () => void };

const useParticipants = (transcriptId: string): UseParticipants => {
  const {
    data: response,
    isLoading: loading,
    error,
    refetch,
  } = useTranscriptParticipants(parseMaybeNonEmptyString(transcriptId));

  // Type-safe return based on state
  if (error) {
    return {
      error: error as Error,
      loading: false,
      response: null,
      refetch,
    } satisfies ErrorParticipants & { refetch: () => void };
  }

  if (loading || !response) {
    return {
      response: response || null,
      loading: true,
      error: null,
      refetch,
    } satisfies LoadingParticipants & { refetch: () => void };
  }

  return {
    response,
    loading: false,
    error: null,
    refetch,
  } satisfies SuccessParticipants & { refetch: () => void };
};

export default useParticipants;
