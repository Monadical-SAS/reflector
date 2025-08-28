import { useRoomsList } from "../../lib/api-hooks";
import { Page_Room_ } from "../../api";
import { PaginationPage } from "../browse/_components/Pagination";

type RoomList = {
  response: Page_Room_ | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
};

// Wrapper to maintain backward compatibility
const useRoomList = (page: PaginationPage): RoomList => {
  const { data, isLoading, error, refetch } = useRoomsList(page);

  return {
    response: data || null,
    loading: isLoading,
    error: error as Error | null,
    refetch,
  };
};

export default useRoomList;
