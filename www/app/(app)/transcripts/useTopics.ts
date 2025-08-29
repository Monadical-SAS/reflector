import { useTranscriptTopics } from "../../lib/api-hooks";
import { GetTranscriptTopic } from "../../lib/api-types";

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
