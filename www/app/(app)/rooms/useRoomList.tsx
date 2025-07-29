import { useEffect, useState } from "react";
import { useError } from "../../(errors)/errorContext";
import useApi from "../../lib/useApi";
import { PageRoom } from "../../api";

type RoomList = {
  response: PageRoom | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
};

//always protected
const useRoomList = (page: number): RoomList => {
  const [response, setResponse] = useState<PageRoom | null>(null);
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
      .v1RoomsList({ page })
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

export default useRoomList;
