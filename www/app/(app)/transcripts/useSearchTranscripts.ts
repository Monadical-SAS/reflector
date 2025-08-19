// this hook is not great, we want to substitute it with a proper state management solution that is also not re-invention

import { useEffect, useRef, useState } from "react";
import { SearchResult, SourceKind } from "../../api";
import useApi from "../../lib/useApi";

interface SearchFilters {
  roomIds?: readonly string[];
  sourceKind?: SourceKind | null;
  status?: string;
  startDate?: string;
  endDate?: string;
}

interface UseSearchTranscriptsOptions {
  pageSize?: number;
}

interface UseSearchTranscriptsReturn {
  results: SearchResult[];
  totalCount: number;
  isLoading: boolean;
  error: unknown;
  hasMore: boolean;
  page: number;
  setPage: (page: number) => void;
}

function hashEffectFilters(filters: SearchFilters): string {
  return JSON.stringify(filters);
}

export function useSearchTranscripts(
  query: string = "",
  filters: SearchFilters = {},
  options: UseSearchTranscriptsOptions = {},
): UseSearchTranscriptsReturn {
  const { pageSize = 20 } = options;

  const api = useApi();
  const abortControllerRef = useRef<AbortController>();

  const [page, setPage] = useState(0);

  const [data, setData] = useState<{ results: SearchResult[]; total: number }>({
    results: [],
    total: 0,
  });
  const [error, setError] = useState<any>();
  const [isLoading, setIsLoading] = useState(false);

  const filterHash = hashEffectFilters(filters);
  useEffect(() => {
    setPage(0);
  }, [query, filterHash]);

  useEffect(() => {
    if (!api) {
      setData({ results: [], total: 0 });
      setError(undefined);
      setIsLoading(false);
      return;
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    const performSearch = async () => {
      setIsLoading(true);

      try {
        const response = await api.v1TranscriptsSearch({
          q: query || "",
          limit: pageSize,
          offset: page * pageSize,
          roomId: filters.roomIds?.[0],
          sourceKind: filters.sourceKind || undefined,
        });

        if (abortController.signal.aborted) return;
        setData(response);
        setError(undefined);
      } catch (err: unknown) {
        if ((err as Error).name === "AbortError") {
          return;
        }
        if (abortController.signal.aborted) {
          console.error("Aborted search but error", err);
          return;
        }

        setError(err);
      } finally {
        if (!abortController.signal.aborted) {
          setIsLoading(false);
        }
      }
    };

    performSearch().then(() => {});

    return () => {
      abortController.abort();
    };
  }, [api, query, page, filterHash, pageSize]);

  const hasMore = (page + 1) * pageSize < data.total;

  return {
    results: data.results,
    totalCount: data.total,
    isLoading,
    error,
    hasMore,
    page,
    setPage,
  };
}
