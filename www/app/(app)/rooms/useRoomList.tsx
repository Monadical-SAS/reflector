import { useEffect, useState } from "react";
import { useError } from "../../(errors)/errorContext";
import useApi from "../../lib/useApi";
import { Page_RoomDetails_ } from "../../api";
import { PaginationPage } from "../browse/_components/Pagination";

type RoomList = {
  response: Page_RoomDetails_ | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
};

//always protected
const useRoomList = (page: PaginationPage): RoomList => {
  const [response, setResponse] = useState<Page_RoomDetails_ | null>(null);
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
