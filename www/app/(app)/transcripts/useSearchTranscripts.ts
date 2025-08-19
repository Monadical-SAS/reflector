import { useState, useEffect, useCallback, useRef, useReducer } from "react";
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
  const abortControllerRef = useRef<AbortController>();

  // Use reducer for immutable state management
  const [state, dispatch] = useReducer(searchReducer, {
    query: initialQuery,
    debouncedQuery: initialQuery, // Start with initial query
    filters: initialFilters,
    page: 0,
  });

  // Search results state
  const [data, setData] = useState<{ results: SearchResult[]; total: number }>({
    results: [],
    total: 0,
  });
  const [error, setError] = useState<any>();
  const [isLoading, setIsLoading] = useState(false);
  const [isValidating, setIsValidating] = useState(false);

  // Update internal state when props change
  useEffect(() => {
    dispatch({ type: "SET_QUERY", payload: initialQuery });
    dispatch({ type: "SET_DEBOUNCED_QUERY", payload: initialQuery });
  }, [initialQuery]);

  useEffect(() => {
    dispatch({ type: "SET_FILTERS", payload: initialFilters });
  }, [JSON.stringify(initialFilters)]); // Use JSON.stringify for deep comparison

  // Debounce query changes
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

  // Perform search when debounced query, page, or filters change
  useEffect(() => {
    if (!api) {
      setData({ results: [], total: 0 });
      setError(undefined);
      setIsLoading(false);
      setIsValidating(false);
      return;
    }

    // Cancel any in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    const performSearch = async () => {
      setIsLoading(true);
      setIsValidating(true);

      try {
        // Validate filters before sending
        if (
          state.filters.startDate &&
          !validateISODate(state.filters.startDate)
        ) {
          console.warn(`Invalid start date format: ${state.filters.startDate}`);
        }
        if (state.filters.endDate && !validateISODate(state.filters.endDate)) {
          console.warn(`Invalid end date format: ${state.filters.endDate}`);
        }

        const response = await api.v1TranscriptsSearch({
          q: state.debouncedQuery || "",
          limit: pageSize,
          offset: state.page * pageSize,
          roomId: state.filters.roomIds?.[0],
          sourceKind: state.filters.sourceKind || undefined,
        });

        // Check if request was aborted
        if (abortController.signal.aborted) {
          return;
        }

        const parsedData = parseSearchResponse(response);
        setData(parsedData);
        setError(undefined);
      } catch (err: any) {
        // Check if request was aborted
        if (abortController.signal.aborted || err.name === "AbortError") {
          return;
        }

        setError(err);
        // Clear data on error
        setData({ results: [], total: 0 });
      } finally {
        if (!abortController.signal.aborted) {
          setIsLoading(false);
          setIsValidating(false);
        }
      }
    };

    performSearch();

    return () => {
      abortController.abort();
    };
  }, [api, state.debouncedQuery, state.page, state.filters, pageSize]);

  // Action dispatchers
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

  // Computed values
  const hasMore = (state.page + 1) * pageSize < data.total;

  return {
    results: data.results,
    totalCount: data.total,
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
