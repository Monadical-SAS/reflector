import { useEffect, useState } from "react";
import { useError } from "../../(errors)/errorContext";
import useApi from "../../lib/useApi";
import { PageGetTranscriptMinimal, SourceKind } from "../../api";

type TranscriptList = {
  response: PageGetTranscriptMinimal | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
};

const useTranscriptList = (
  page: number,
  sourceKind: SourceKind | null,
  roomId: string | null,
  searchTerm: string | null,
): TranscriptList => {
  const [response, setResponse] = useState<PageGetTranscriptMinimal | null>(
    null,
  );
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setErrorState] = useState<Error | null>(null);
  const { setError } = useError();
  const api = useApi();
  const [refetchCount, setRefetchCount] = useState(0);

  const refetch = () => {
    setLoading(true);
    setRefetchCount(refetchCount + 1);
  };

  useEffect(() => {
    if (!api) return;
    setLoading(true);
    api
      .v1TranscriptsList({
        page,
        sourceKind,
        roomId,
        searchTerm,
        size: 10,
      })
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
  }, [api, page, refetchCount, roomId, searchTerm, sourceKind]);

  return { response, loading, error, refetch };
};

export default useTranscriptList;
