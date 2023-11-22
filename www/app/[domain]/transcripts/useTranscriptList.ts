import { useEffect, useState } from "react";
import { GetTranscriptFromJSON, PageGetTranscript } from "../../api";
import { useError } from "../../(errors)/errorContext";
import getApi from "../../lib/getApi";

type TranscriptList = {
  response: PageGetTranscript | null;
  loading: boolean;
  error: Error | null;
};

//always protected
const useTranscriptList = (page: number): TranscriptList => {
  const [response, setResponse] = useState<PageGetTranscript | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setErrorState] = useState<Error | null>(null);
  const { setError } = useError();
  const api = getApi();

  useEffect(() => {
    if (!api) return;
    setLoading(true);
    api
      .v1TranscriptsList({ page })
      .then((response) => {
        // issue with API layer, conversion for items is not happening
        response.items = response.items.map((item) =>
          GetTranscriptFromJSON(item),
        );
        setResponse(response);
        setLoading(false);
      })
      .catch((err) => {
        setResponse(null);
        setLoading(false);
        setError(err);
        setErrorState(err);
      });
  }, [!api, page]);

  return { response, loading, error };
};

export default useTranscriptList;
