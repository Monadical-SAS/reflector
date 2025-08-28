import { useEffect, useState } from "react";

import { GetTranscriptTopicWithWordsPerSpeaker } from "../../lib/api-types";
import { useError } from "../../(errors)/errorContext";
import useApi from "../../lib/useApi";
import { shouldShowError } from "../../lib/errorUtils";

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
  const [response, setResponse] =
    useState<GetTranscriptTopicWithWordsPerSpeaker | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setErrorState] = useState<Error | null>(null);
  const { setError } = useError();
  const api = useApi();

  const [count, setCount] = useState(0);

  const refetch = () => {
    if (!loading) {
      setCount(count + 1);
      setLoading(true);
      setErrorState(null);
    }
  };

  useEffect(() => {
    if (!transcriptId || !topicId || !api) return;

    setLoading(true);

    api
      .v1TranscriptGetTopicsWithWordsPerSpeaker({ transcriptId, topicId })
      .then((result) => {
        setResponse(result);
        setLoading(false);
        console.debug("Topics with words Loaded:", result);
      })
      .catch((error) => {
        const shouldShowHuman = shouldShowError(error);
        if (shouldShowHuman) {
          setError(error, "There was an error loading the topics with words");
        } else {
          setError(error);
        }
        setErrorState(error);
      });
  }, [transcriptId, !api, topicId, count]);

  return { response, loading, error, refetch } as UseTopicWithWords;
};

export default useTopicWithWords;
