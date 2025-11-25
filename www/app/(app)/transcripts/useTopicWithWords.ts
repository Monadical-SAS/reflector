import type { components } from "../../reflector-api";
import { useTranscriptTopicsWithWordsPerSpeaker } from "../../lib/apiHooks";

type GetTranscriptTopicWithWordsPerSpeaker =
  components["schemas"]["GetTranscriptTopicWithWordsPerSpeaker"];

type ErrorTopicWithWords = {
  error: Error;
  loading: false;
  response: null;
};

type LoadingTopicWithWords = {
  response: GetTranscriptTopicWithWordsPerSpeaker | null;
  loading: true;
  error: false;
};

type SuccessTopicWithWords = {
  response: GetTranscriptTopicWithWordsPerSpeaker;
  loading: false;
  error: null;
};

export type UseTopicWithWords = { refetch: () => void } & (
  | ErrorTopicWithWords
  | LoadingTopicWithWords
  | SuccessTopicWithWords
);

const useTopicWithWords = (
  topicId: string | undefined,
  transcriptId: string,
): UseTopicWithWords => {
  const {
    data: response,
    isLoading: loading,
    error,
    refetch,
  } = useTranscriptTopicsWithWordsPerSpeaker(
    transcriptId || null,
    topicId || null,
  );

  if (error) {
    return {
      error: error as Error,
      loading: false,
      response: null,
      refetch,
    } satisfies ErrorTopicWithWords & { refetch: () => void };
  }

  if (loading || !response) {
    return {
      response: response || null,
      loading: true,
      error: false,
      refetch,
    } satisfies LoadingTopicWithWords & { refetch: () => void };
  }

  return {
    response,
    loading: false,
    error: null,
    refetch,
  } satisfies SuccessTopicWithWords & { refetch: () => void };
};

export default useTopicWithWords;
