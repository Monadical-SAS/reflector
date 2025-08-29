// Wrapper for backward compatibility
import { SearchResult, SourceKind } from "../../lib/api-types";
import { useTranscriptsSearch } from "../../lib/api-hooks";
import {
  PaginationPage,
  paginationPageTo0Based,
} from "../browse/_components/Pagination";

interface SearchFilters {
  roomIds: readonly string[] | null;
  sourceKind: SourceKind | null;
}

type UseSearchTranscriptsOptions = {
  pageSize: number;
  page: PaginationPage;
};

interface UseSearchTranscriptsReturn {
  results: SearchResult[];
  totalCount: number;
  isLoading: boolean;
  error: unknown;
  reload: () => void;
}

export function useSearchTranscripts(
  query: string = "",
  filters: SearchFilters = { roomIds: null, sourceKind: null },
  options: UseSearchTranscriptsOptions = {
    pageSize: 20,
    page: PaginationPage(1),
  },
): UseSearchTranscriptsReturn {
  const { pageSize, page } = options;

  const { data, isLoading, error, refetch } = useTranscriptsSearch(query, {
    limit: pageSize,
    offset: paginationPageTo0Based(page) * pageSize,
    room_id: filters.roomIds?.[0],
    source_kind: filters.sourceKind || undefined,
  });

  return {
    results: data?.results || [],
    totalCount: data?.total || 0,
    isLoading,
    error,
    reload: refetch,
  };
}
