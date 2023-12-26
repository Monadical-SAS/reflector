import { useEffect, useState } from "react";
import { useError } from "../../(errors)/errorContext";
import useApi from "../../lib/useApi";
import { Page_GetTranscript_ } from "../../api";

type TranscriptList = {
  response: Page_GetTranscript_ | null;
  loading: boolean;
  error: Error | null;
};

//always protected
const useTranscriptList = (page: number): TranscriptList => {
  const [response, setResponse] = useState<Page_GetTranscript_ | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setErrorState] = useState<Error | null>(null);
  const { setError } = useError();
  const api = useApi();

  useEffect(() => {
    setLoading(true);
    if (!api) return;
    api
      .v1TranscriptsList(page)
      .then((response) => {
        setResponse(response);
        setLoading(false);
      })
      .catch((err) => {
        setResponse(null);
        setLoading(false);
        setError(err);
        setErrorState(err);
      });
  }, [api, page]);

  return { response, loading, error };
};

export default useTranscriptList;
