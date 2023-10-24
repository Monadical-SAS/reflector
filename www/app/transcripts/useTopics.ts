import { useEffect, useState } from "react";
import {
  DefaultApi,
  V1TranscriptGetTopicsRequest,
} from "../api/apis/DefaultApi";
import { TranscriptTopic } from "../api";
import { useError } from "../(errors)/errorContext";
import { Topic } from "./webSocketTypes";

type TranscriptTopics = {
  topics: Topic[] | null;
  loading: boolean;
  error: Error | null;
};

const useTopics = (api: DefaultApi, id: string): TranscriptTopics => {
  const [topics, setTopics] = useState<Topic[] | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setErrorState] = useState<Error | null>(null);
  const { setError } = useError();

  const getTopics = (id: string) => {
    if (!id) return;

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
  };

  useEffect(() => {
    getTopics(id);
  }, [id]);

  return { topics, loading, error };
};

export default useTopics;
