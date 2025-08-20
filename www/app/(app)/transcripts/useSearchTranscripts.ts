// this hook is not great, we want to substitute it with a proper state management solution that is also not re-invention

import { useEffect, useRef, useState } from "react";
import { parseSearchResult, SearchResult } from "../../api/types";
import { SourceKind } from "../../api";
import useApi from "../../lib/useApi";
import {
  PaginationPage,
  paginationPageTo0Based,
} from "../browse/_components/Pagination";

interface SearchFilters {
  roomIds: readonly string[] | null;
  sourceKind: SourceKind | null;
}

const EMPTY_SEARCH_FILTERS: SearchFilters = {
  roomIds: null,
  sourceKind: null,
};

type UseSearchTranscriptsOptions = {
  pageSize: number;
  page: PaginationPage;
};

interface UseSearchTranscriptsReturn {
  results: SearchResult[];
  totalCount: number;
  isLoading: boolean;
  error: unknown;
}

function hashEffectFilters(filters: SearchFilters): string {
  return JSON.stringify(filters);
}

export function useSearchTranscripts(
  query: string = "",
  filters: SearchFilters = EMPTY_SEARCH_FILTERS,
  options: UseSearchTranscriptsOptions = {
    pageSize: 20,
    page: PaginationPage(1),
  },
): UseSearchTranscriptsReturn {
  const { pageSize, page } = options;

  const api = useApi();
  const abortControllerRef = useRef<AbortController>();

  const [data, setData] = useState<{ results: SearchResult[]; total: number }>({
    results: [],
    total: 0,
  });
  const [error, setError] = useState<any>();
  const [isLoading, setIsLoading] = useState(false);

  const filterHash = hashEffectFilters(filters);

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
          offset: paginationPageTo0Based(page) * pageSize,
          roomId: filters.roomIds?.[0],
          sourceKind: filters.sourceKind || undefined,
        });

        if (abortController.signal.aborted) return;
        setData({
          ...response,
          results: response.results.map(parseSearchResult),
        });
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

  return {
    results: data.results,
    totalCount: data.total,
    isLoading,
    error,
  };
}
