import { useEffect, useState } from "react";
import { V1TranscriptGetRequest } from "../../api/apis/DefaultApi";
import { GetTranscript } from "../../api";
import { useError } from "../../(errors)/errorContext";
import getApi from "../../lib/getApi";

type Transcript = {
  response: GetTranscript | null;
  loading: boolean;
  error: Error | null;
};

const useTranscript = (id: string | null): Transcript => {
  const [response, setResponse] = useState<GetTranscript | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setErrorState] = useState<Error | null>(null);
  const { setError } = useError();
  const api = getApi(false);
  useEffect(() => {
    if (!id || !api) return;

    setLoading(true);
    const requestParameters: V1TranscriptGetRequest = {
      transcriptId: id,
    };
    api
      .v1TranscriptGet(requestParameters)
      .then((result) => {
        setResponse(result);
        setLoading(false);
        console.debug("Transcript Loaded:", result);
      })
      .catch((error) => {
        if (error?.name == "ResponseError" && error["response"].status == 403) {
          return;
        }
        setError(error);
        setErrorState(error);
      });
  }, [id, api]);

  return { response, loading, error };
};

export default useTranscript;
