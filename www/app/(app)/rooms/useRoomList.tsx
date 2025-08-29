import { useRoomsList } from "../../lib/api-hooks";
import type { components } from "../../reflector-api";

type Page_Room_ = components["schemas"]["Page_Room_"];
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
