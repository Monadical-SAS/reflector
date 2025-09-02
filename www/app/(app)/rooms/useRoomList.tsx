import { useRoomsList } from "../../lib/apiHooks";
import type { components } from "../../reflector-api";

type Page_Room_ = components["schemas"]["Page_RoomDetails_"];
import { PaginationPage } from "../browse/_components/Pagination";

type RoomList = {
  response: Page_Room_ | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
};

type ValidationError = components["schemas"]["ValidationError"];

const formatValidationErrors = (errors: ValidationError[]) => {
  return errors.map((error) => error.msg).join(", ");
};

// Wrapper to maintain backward compatibility
const useRoomList = (page: PaginationPage): RoomList => {
  const { data, isLoading, error, refetch } = useRoomsList(page);

  return {
    response: data || null,
    loading: isLoading,
    error: error
      ? new Error(
          error.detail ? formatValidationErrors(error.detail) : undefined,
        )
      : null,
    refetch,
  };
};

export default useRoomList;
