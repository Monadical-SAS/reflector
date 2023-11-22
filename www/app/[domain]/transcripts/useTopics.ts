import { useEffect, useState } from "react";
import {
  DefaultApi,
  V1TranscriptGetTopicsRequest,
} from "../../api/apis/DefaultApi";
import { useError } from "../../(errors)/errorContext";
import { Topic } from "./webSocketTypes";
import getApi from "../../lib/getApi";
import { shouldShowError } from "../../lib/errorUtils";

type TranscriptTopics = {
  topics: Topic[] | null;
  loading: boolean;
  error: Error | null;
};

const useTopics = (id: string): TranscriptTopics => {
  const [topics, setTopics] = useState<Topic[] | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setErrorState] = useState<Error | null>(null);
  const { setError } = useError();
  const api = getApi();

  useEffect(() => {
    if (!id || !api) return;

    setLoading(true);
    const requestParameters: V1TranscriptGetTopicsRequest = {
      transcriptId: id,
    };
    api
      .v1TranscriptGetTopics(requestParameters)
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
