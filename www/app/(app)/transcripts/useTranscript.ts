import type { components } from "../../reflector-api";
import { useTranscriptGet } from "../../lib/apiHooks";

type GetTranscript = components["schemas"]["GetTranscript"];

type ErrorTranscript = {
  error: Error;
  loading: false;
  response: null;
  reload: () => void;
};

type LoadingTranscript = {
  response: null;
  loading: true;
  error: false;
  reload: () => void;
};

type SuccessTranscript = {
  response: GetTranscript;
  loading: false;
  error: null;
  reload: () => void;
};

const useTranscript = (
  id: string | null,
): ErrorTranscript | LoadingTranscript | SuccessTranscript => {
  const { data, isLoading, error, refetch } = useTranscriptGet(id);

  // Map to the expected return format
  if (isLoading) {
    return {
      response: null,
      loading: true,
      error: false,
      reload: refetch,
    };
  }

  if (error) {
    return {
      error: error as Error,
      loading: false,
      response: null,
      reload: refetch,
    };
  }

  // Check if data is undefined or null
  if (!data) {
    return {
      response: null,
      loading: true,
      error: false,
      reload: refetch,
    };
  }

  return {
    response: data,
    loading: false,
    error: null,
    reload: refetch,
  };
};

export default useTranscript;
