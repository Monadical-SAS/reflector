import { useEffect, useState } from "react";
import {
  V1TranscriptGetTopicsWithWordsPerSpeakerRequest,
  V1TranscriptGetTopicsWithWordsRequest,
} from "../../api/apis/DefaultApi";
import {
  GetTranscript,
  GetTranscriptTopicWithWords,
  GetTranscriptTopicWithWordsPerSpeaker,
} from "../../api";
import { useError } from "../../(errors)/errorContext";
import getApi from "../../lib/getApi";
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
  topicId: string | null,
  transcriptId: string,
): UseTopicWithWords => {
  const [response, setResponse] =
    useState<GetTranscriptTopicWithWordsPerSpeaker | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setErrorState] = useState<Error | null>(null);
  const { setError } = useError();
  const api = getApi();

  const [count, setCount] = useState(0);

  const refetch = () => {
    setCount(count + 1);
    setLoading(true);
    setErrorState(null);
  };

  useEffect(() => {
    setLoading(true);
  }, [transcriptId, topicId]);

  useEffect(() => {
    if (!transcriptId || !topicId || !api) return;

    setLoading(true);
    const requestParameters: V1TranscriptGetTopicsWithWordsPerSpeakerRequest = {
      transcriptId,
      topicId,
    };
    api
      .v1TranscriptGetTopicsWithWordsPerSpeaker(requestParameters)
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
