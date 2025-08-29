import { useTranscriptTopics } from "../../lib/apiHooks";
import type { components } from "../../reflector-api";

type GetTranscriptTopic = components["schemas"]["GetTranscriptTopic"];

type TranscriptTopics = {
  topics: GetTranscriptTopic[] | null;
  loading: boolean;
  error: Error | null;
};

const useTopics = (id: string): TranscriptTopics => {
  const { data: topics, isLoading: loading, error } = useTranscriptTopics(id);

  return {
    topics: topics || null,
    loading,
    error: error as Error | null,
  };
};

export default useTopics;
