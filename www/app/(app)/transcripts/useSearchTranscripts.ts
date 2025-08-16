import { useState, useEffect, useCallback, useRef } from "react";
import useSWR from "swr";
import { SearchResult, SourceKind } from "../../api";
import useApi from "../../lib/useApi";

interface SearchFilters {
  roomIds?: string[];
  sourceKind?: SourceKind | null;
  status?: string;
  startDate?: string;
  endDate?: string;
}

interface UseSearchTranscriptsOptions {
  debounceMs?: number;
  pageSize?: number;
}

interface UseSearchTranscriptsReturn {
  results: SearchResult[];
  totalCount: number;
  isLoading: boolean;
  isValidating: boolean;
  error: any;
  hasMore: boolean;
  page: number;
  query: string;
  setPage: (page: number) => void;
  setQuery: (query: string) => void;
  setFilters: (filters: SearchFilters) => void;
  clearSearch: () => void;
}

export function useSearchTranscripts(
  initialQuery: string = "",
  initialFilters: SearchFilters = {},
  options: UseSearchTranscriptsOptions = {},
): UseSearchTranscriptsReturn {
  const { debounceMs = 300, pageSize = 20 } = options;

  const api = useApi();
  const [query, setQueryState] = useState(initialQuery);
  const [debouncedQuery, setDebouncedQuery] = useState(initialQuery);
  const [filters, setFilters] = useState<SearchFilters>(initialFilters);
  const [page, setPage] = useState(0);
  const debounceTimerRef = useRef<NodeJS.Timeout>();

  // Debounce query changes
  useEffect(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    if (debounceMs === 0) {
      setDebouncedQuery(query);
    } else {
      debounceTimerRef.current = setTimeout(() => {
        setDebouncedQuery(query);
      }, debounceMs);
    }

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [query, debounceMs]);

  // SWR fetcher
  const fetcher = useCallback(
    async (key: string) => {
      if (!api) return { results: [], total: 0 };

      const [_, searchQuery, pageNum, filterKey] = key.split(":");

      // Always use search endpoint, with empty query for browsing
      const response = await api.v1TranscriptsSearch({
        q: searchQuery || "", // Empty string for browsing all transcripts
        limit: pageSize,
        offset: parseInt(pageNum) * pageSize,
        roomId: filters.roomIds?.[0] || undefined, // Pass room filter to search API
      });

      return {
        results: response.results || [],
        total: response.total || 0,
      };
    },
    [api, filters, pageSize],
  );

  // Use SWR for data fetching - include filters in key for proper caching
  const filterKey = JSON.stringify(filters);
  const swrKey =
    api && debouncedQuery !== undefined
      ? `search:${debouncedQuery}:${page}:${filterKey}`
      : null;

  const { data, error, isLoading, isValidating } = useSWR(swrKey, fetcher, {
    keepPreviousData: true,
    revalidateOnFocus: false,
  });

  const setQuery = useCallback((newQuery: string) => {
    setQueryState(newQuery);
    setPage(0); // Reset to first page on new search
  }, []);

  const clearSearch = useCallback(() => {
    setQueryState("");
    setDebouncedQuery("");
    setPage(0);
    setFilters({});
  }, []);

  const results = data?.results || [];
  const totalCount = data?.total || 0;
  const hasMore = (page + 1) * pageSize < totalCount;

  return {
    results,
    totalCount,
    isLoading,
    isValidating,
    error,
    hasMore,
    page,
    query: debouncedQuery,
    setPage,
    setQuery,
    setFilters,
    clearSearch,
  };
}
