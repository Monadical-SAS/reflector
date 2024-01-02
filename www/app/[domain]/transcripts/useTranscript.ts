import { useEffect, useState } from "react";
import { GetTranscript } from "../../api";
import { useError } from "../../(errors)/errorContext";
import { shouldShowError } from "../../lib/errorUtils";
import useApi from "../../lib/useApi";

type ErrorTranscript = {
  error: Error;
  loading: false;
  response: any;
};

type LoadingTranscript = {
  response: any;
  loading: true;
  error: false;
};

type SuccessTranscript = {
  response: GetTranscript;
  loading: false;
  error: null;
};

const useTranscript = (
  id: string | null,
): ErrorTranscript | LoadingTranscript | SuccessTranscript => {
  const [response, setResponse] = useState<GetTranscript | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setErrorState] = useState<Error | null>(null);
  const { setError } = useError();
  const api = useApi();

  useEffect(() => {
    if (!id || !api) return;

    setLoading(true);

    api
      .v1TranscriptGet(id)
      .then((result) => {
        setResponse(result);
        setLoading(false);
        console.debug("Transcript Loaded:", result);
      })
      .catch((error) => {
        const shouldShowHuman = shouldShowError(error);
        if (shouldShowHuman) {
          setError(error, "There was an error loading the transcript");
        } else {
          setError(error);
        }
        setErrorState(error);
      });
  }, [id, !api]);

  return { response, loading, error } as
    | ErrorTranscript
    | LoadingTranscript
    | SuccessTranscript;
};

export default useTranscript;
