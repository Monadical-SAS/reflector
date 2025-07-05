import { useEffect, useState, useRef } from "react";
import { Participant, CancelablePromise } from "../../api";
import { useError } from "../../(errors)/errorContext";
import useApi from "../../lib/useApi";
import { shouldShowError } from "../../lib/errorUtils";

type ErrorParticipants = {
  error: Error;
  loading: false;
  response: null;
};

type LoadingParticipants = {
  response: Participant[] | null;
  loading: true;
  error: null;
};

type SuccessParticipants = {
  response: Participant[];
  loading: boolean;
  error: null;
};

export type UseParticipants = (
  | ErrorParticipants
  | LoadingParticipants
  | SuccessParticipants
) & { refetch: () => void };

const useParticipants = (transcriptId: string): UseParticipants => {
  const [response, setResponse] = useState<Participant[] | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setErrorState] = useState<Error | null>(null);
  const { setError } = useError();
  const api = useApi();
  const [count, setCount] = useState(0);
  const requestRef = useRef<CancelablePromise<Participant[]> | null>(null);

  const refetch = () => {
    if (!loading) {
      if (requestRef.current) {
        requestRef.current.cancel();
      }
      setCount(count + 1);
      setLoading(true);
      setErrorState(null);
    }
  };

  useEffect(() => {
    if (!transcriptId || !api) return;

    if (requestRef.current) {
      requestRef.current.cancel();
    }

    setLoading(true);
    requestRef.current = api.v1TranscriptGetParticipants({ transcriptId });
    
    requestRef.current
      .then((result) => {
        setResponse(result);
        setLoading(false);
        console.debug("Participants Loaded:", result);
      })
      .catch((error) => {
        if (error.name === "CancelError") {
          return;
        }
        const shouldShowHuman = shouldShowError(error);
        if (shouldShowHuman) {
          setError(error, "There was an error loading the participants");
        } else {
          setError(error);
        }
        setErrorState(error);
        setResponse(null);
        setLoading(false);
      });

    return () => {
      if (requestRef.current) {
        requestRef.current.cancel();
      }
    };
  }, [transcriptId, !api, count]);

  return { response, loading, error, refetch } as UseParticipants;
};

export default useParticipants;
