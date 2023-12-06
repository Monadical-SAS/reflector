import { useEffect, useState } from "react";
import { useError } from "../../(errors)/errorContext";
import useApi from "../../lib/useApi";
import { Page_GetTranscript_ } from "../../api";

type TranscriptList = {
  response: Page_GetTranscript_ | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
};

//always protected
const useTranscriptList = (page: number): TranscriptList => {
  const [response, setResponse] = useState<Page_GetTranscript_ | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setErrorState] = useState<Error | null>(null);
  const { setError } = useError();
  const api = useApi();
  const [refetchCount, setRefetchCount] = useState(0);

  const refetch = () => {
    setRefetchCount(refetchCount + 1);
  };

  useEffect(() => {
    setResponse(null);
  }, [page]);

  useEffect(() => {
    if (!api) return;
    setLoading(true);
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
  }, [!api, page, refetchCount]);

  return { response, loading, error, refetch };
};

export default useTranscriptList;
