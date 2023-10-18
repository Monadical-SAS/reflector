import { useEffect, useState } from "react";
import {
  DefaultApi,
  V1TranscriptGetTopicsRequest,
} from "../../api/apis/DefaultApi";
import { useError } from "../../(errors)/errorContext";
import { Topic } from "./webSocketTypes";
import getApi from "../../lib/getApi";

type TranscriptTopics = {
  topics: Topic[] | null;
  loading: boolean;
  error: Error | null;
};

const useTopics = (protectedPath, id: string): TranscriptTopics => {
  const [topics, setTopics] = useState<Topic[] | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setErrorState] = useState<Error | null>(null);
  const { setError } = useError();
  const api = getApi(protectedPath);

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
        setError(err);
        setErrorState(err);
      });
  }, [id, api]);

  return { topics, loading, error };
};

export default useTopics;
