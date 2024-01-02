import { useEffect, useState } from "react";
import { Participant } from "../../api";
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
  error: false;
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

  const refetch = () => {
    if (!loading) {
      setCount(count + 1);
      setLoading(true);
      setErrorState(null);
    }
  };

  useEffect(() => {
    if (!transcriptId || !api) return;

    setLoading(true);
    api
      .v1TranscriptGetParticipants(transcriptId)
      .then((result) => {
        setResponse(result);
        setLoading(false);
        console.debug("Participants Loaded:", result);
      })
      .catch((error) => {
        const shouldShowHuman = shouldShowError(error);
        if (shouldShowHuman) {
          setError(error, "There was an error loading the participants");
        } else {
          setError(error);
        }
        setErrorState(error);
      });
  }, [transcriptId, !api, count]);

  return { response, loading, error, refetch } as UseParticipants;
};

export default useParticipants;
