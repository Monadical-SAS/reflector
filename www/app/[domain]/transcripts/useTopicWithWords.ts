import { useEffect, useState } from "react";
import { V1TranscriptGetTopicsWithWordsRequest } from "../../api/apis/DefaultApi";
import { GetTranscript, GetTranscriptTopicWithWords } from "../../api";
import { useError } from "../../(errors)/errorContext";
import getApi from "../../lib/getApi";
import { shouldShowError } from "../../lib/errorUtils";

type ErrorTopicWithWords = {
  error: Error;
  loading: false;
  response: any;
};

type LoadingTopicWithWords = {
  response: any;
  loading: true;
  error: false;
};

type SuccessTopicWithWords = {
  response: GetTranscriptTopicWithWords;
  loading: false;
  error: null;
};

const useTopicWithWords = (
  topicId: string | null,
  transcriptId: string,
): ErrorTopicWithWords | LoadingTopicWithWords | SuccessTopicWithWords => {
  const [response, setResponse] = useState<GetTranscript | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setErrorState] = useState<Error | null>(null);
  const { setError } = useError();
  const api = getApi();

  useEffect(() => {
    setLoading(true);
  }, [transcriptId, topicId]);

  useEffect(() => {
    if (!transcriptId || !topicId || !api) return;

    setLoading(true);
    const requestParameters: V1TranscriptGetTopicsWithWordsRequest = {
      transcriptId,
    };
    api
      .v1TranscriptGetTopicsWithWords(requestParameters)
      .then((result) => {
        setResponse(result.find((topic) => topic.id == topicId));
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
  }, [transcriptId, !api, topicId]);

  return { response, loading, error } as
    | ErrorTopicWithWords
    | LoadingTopicWithWords
    | SuccessTopicWithWords;
};

export default useTopicWithWords;
