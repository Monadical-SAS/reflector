import { useEffect, useState } from "react";

import { useError } from "../../(errors)/errorContext";
import { Topic } from "./webSocketTypes";
import useApi from "../../lib/useApi";
import { shouldShowError } from "../../lib/errorUtils";
import { GetTranscriptTopic } from "../../api";

type TranscriptTopics = {
  topics: GetTranscriptTopic[] | null;
  loading: boolean;
  error: Error | null;
};

const useTopics = (id: string): TranscriptTopics => {
  const [topics, setTopics] = useState<Topic[] | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setErrorState] = useState<Error | null>(null);
  const { setError } = useError();
  const api = useApi();

  useEffect(() => {
    if (!id || !api) return;

    setLoading(true);
    api
      .v1TranscriptGetTopics(id)
      .then((result) => {
        setTopics(result);
        setLoading(false);
        console.debug("Transcript topics loaded:", result);
      })
      .catch((err) => {
        setErrorState(err);
        const shouldShowHuman = shouldShowError(err);
        if (shouldShowHuman) {
          setError(err, "There was an error loading the topics");
        } else {
          setError(err);
        }
      });
  }, [id, api]);

  return { topics, loading, error };
};

export default useTopics;
