import { useState, useEffect, useCallback, useRef, useReducer } from "react";
import useSWR from "swr";
import {
  SearchResult,
  SourceKind,
  V1TranscriptsSearchResponse,
} from "../../api";
import useApi from "../../lib/useApi";

// The API already exports SourceKind as: "room" | "live" | "file"
// We'll use the existing types and only add domain-specific validation where needed

interface SearchFilters {
  roomIds?: readonly string[];
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

// State management with reducer pattern
type SearchAction =
  | { type: "SET_QUERY"; payload: string }
  | { type: "SET_DEBOUNCED_QUERY"; payload: string }
  | { type: "SET_FILTERS"; payload: SearchFilters }
  | { type: "SET_PAGE"; payload: number }
  | { type: "CLEAR_SEARCH" }
  | { type: "RESET_PAGE" };

interface SearchState {
  readonly query: string;
  readonly debouncedQuery: string;
  readonly filters: SearchFilters;
  readonly page: number;
}

const searchReducer = (
  state: SearchState,
  action: SearchAction,
): SearchState => {
  switch (action.type) {
    case "SET_QUERY":
      return { ...state, query: action.payload, page: 0 };
    case "SET_DEBOUNCED_QUERY":
      return { ...state, debouncedQuery: action.payload };
    case "SET_FILTERS":
      return { ...state, filters: action.payload, page: 0 };
    case "SET_PAGE":
      return { ...state, page: action.payload };
    case "RESET_PAGE":
      return { ...state, page: 0 };
    case "CLEAR_SEARCH":
      return {
        query: "",
        debouncedQuery: "",
        filters: {},
        page: 0,
      };
    default:
      return state;
  }
};

const createCacheKey = (
  query: string,
  page: number,
  filters: SearchFilters,
): string => {
  const filterKey = encodeURIComponent(JSON.stringify(filters));
  return `search:${query}:${page}:${filterKey}`;
};

const parseSearchResponse = (response: V1TranscriptsSearchResponse | null) => ({
  results: response?.results || [],
  total: response?.total || 0,
});

// Validation helpers that work with existing types
const validateISODate = (date: string): boolean => {
  return /^\d{4}-\d{2}-\d{2}/.test(date);
};

const validateSourceKind = (kind: string): kind is SourceKind => {
  return kind === "room" || kind === "live" || kind === "file";
};

export function useSearchTranscripts(
  initialQuery: string = "",
  initialFilters: SearchFilters = {},
  options: UseSearchTranscriptsOptions = {},
): UseSearchTranscriptsReturn {
  const { debounceMs = 300, pageSize = 20 } = options;

  const api = useApi();
  const debounceTimerRef = useRef<NodeJS.Timeout>();

  // Use reducer for immutable state management
  const [state, dispatch] = useReducer(searchReducer, {
    query: initialQuery,
    debouncedQuery: "", // Start with empty to ensure initial effect triggers
    filters: initialFilters,
    page: 0,
  });

  // Debounce query changes - pure effect
  useEffect(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    const updateDebouncedQuery = () => {
      dispatch({ type: "SET_DEBOUNCED_QUERY", payload: state.query });
    };

    if (debounceMs === 0) {
      updateDebouncedQuery();
    } else {
      debounceTimerRef.current = setTimeout(updateDebouncedQuery, debounceMs);
    }

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [state.query, debounceMs]);

  // Pure fetcher function
  const fetcher = useCallback(
    async (key: string) => {
      if (!api) return parseSearchResponse(null);

      const [_, searchQuery, pageNum, filterKey] = key.split(":");
      const parsedFilters: SearchFilters = JSON.parse(
        decodeURIComponent(filterKey || "%7B%7D"),
      );

      // Validate filters before sending
      if (
        parsedFilters.startDate &&
        !validateISODate(parsedFilters.startDate)
      ) {
        console.warn(`Invalid start date format: ${parsedFilters.startDate}`);
      }
      if (parsedFilters.endDate && !validateISODate(parsedFilters.endDate)) {
        console.warn(`Invalid end date format: ${parsedFilters.endDate}`);
      }

      const response = await api.v1TranscriptsSearch({
        q: searchQuery || "",
        limit: pageSize,
        offset: parseInt(pageNum) * pageSize,
        roomId: parsedFilters.roomIds?.[0],
        sourceKind: parsedFilters.sourceKind || undefined,
      });

      return parseSearchResponse(response);
    },
    [api, pageSize],
  );

  // Use SWR for data fetching with pure key generation
  const swrKey = api
    ? createCacheKey(state.debouncedQuery, state.page, state.filters)
    : null;

  const { data, error, isLoading, isValidating } = useSWR(swrKey, fetcher, {
    keepPreviousData: true,
    revalidateOnFocus: false,
  });

  // Action dispatchers - pure functions
  const setQuery = useCallback((newQuery: string) => {
    dispatch({ type: "SET_QUERY", payload: newQuery });
  }, []);

  const setPage = useCallback((newPage: number) => {
    dispatch({ type: "SET_PAGE", payload: newPage });
  }, []);

  const setFilters = useCallback((newFilters: SearchFilters) => {
    // Validate source kind if provided
    if (newFilters.sourceKind && !validateSourceKind(newFilters.sourceKind)) {
      console.warn(`Invalid source kind: ${newFilters.sourceKind}`);
    }
    dispatch({ type: "SET_FILTERS", payload: newFilters });
  }, []);

  const clearSearch = useCallback(() => {
    dispatch({ type: "CLEAR_SEARCH" });
  }, []);

  // Computed values using pure functions
  const results = data?.results || [];
  const totalCount = data?.total || 0;
  const hasMore = (state.page + 1) * pageSize < totalCount;

  return {
    results,
    totalCount,
    isLoading,
    isValidating,
    error,
    hasMore,
    page: state.page,
    query: state.debouncedQuery,
    setPage,
    setQuery,
    setFilters,
    clearSearch,
  };
}

// Export validation helpers for use by consumers
export { validateISODate, validateSourceKind };
